require("dotenv").config();
import express from "express";
import fs from "fs";
import { addWeeks, startOfWeek } from "date-fns";
import {
  renderCalendar,
  renderToPng,
  extractChunk,
  CalendarEvent,
  RenderedCalendar,
  LegendItem,
  DayForecast,
  IndicatorData,
} from "./renderer";
import { startOfDay, parseISO } from "date-fns";
import mdns from "multicast-dns";
import os from "os";

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

const port = process.env.PORT || 4000;
const CONFIG_FILE = process.env.CONFIG_PATH || "./epcal-config.json";

// Add-on mode: HA connection comes from environment (set by Supervisor)
const ADDON_MODE = !!(process.env.HA_URL && process.env.HA_TOKEN);
const INGRESS_PATH = process.env.INGRESS_PATH || "";

// Log mode on startup
if (ADDON_MODE) {
  console.log("Running in Home Assistant Add-on mode");
  console.log(`Ingress path: ${INGRESS_PATH || "(none)"}`);
}

// Get server timezone offset string (e.g., "-05:00")
function getServerTimezoneOffset(): string {
  const offset = new Date().getTimezoneOffset();
  const sign = offset <= 0 ? "+" : "-";
  const hours = Math.floor(Math.abs(offset) / 60)
    .toString()
    .padStart(2, "0");
  const minutes = (Math.abs(offset) % 60).toString().padStart(2, "0");
  return `${sign}${hours}:${minutes}`;
}

// Get server timezone name
function getServerTimezoneName(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

// Configuration interface
interface Config {
  haUrl: string;
  haToken: string;
  enabledCalendars?: string[]; // List of enabled calendar entity_ids
  calendarIcons?: { [entityId: string]: string }; // Calendar icon/letter assignments
  calendarNames?: { [entityId: string]: string }; // Calendar display names for legend
  collectionCalendars?: string[]; // List of calendar entity_ids that are collection calendars (garbage, recycling, etc.)
  collectionTypes?: Array<{
    // Collection types (trash, recycling, compost, etc.) with icons
    name: string; // Name/keyword to match in event title (e.g., "Garbage", "Recycling")
    icon: string; // Icon to display (emoji)
  }>;
  layout?: "portrait" | "landscape"; // Display layout mode
  weatherEntity?: string; // Weather entity for forecast display
  showLegend?: boolean; // Show calendar legend on display
  displayIndicators?: Array<{
    entityId: string;
    label: string;
    icon: string;
    showWhen: "on" | "off" | "always";
  }>;
}

// Layout options for UI
const LAYOUT_OPTIONS = [
  {
    value: "landscape",
    label: "Paysage (recommandé)",
    description: "Aujourd'hui à gauche, 6 jours + à venir à droite",
  },
  {
    value: "portrait",
    label: "Portrait",
    description: "Aujourd'hui en haut, semaine au milieu, à venir en bas",
  },
];

// Available icons for calendars (single characters)
const CALENDAR_ICONS = [
  "●",
  "■",
  "▲",
  "◆",
  "★",
  "♦",
  "♣",
  "♠",
  "○",
  "□",
  "△",
  "◇",
  "☆",
  "⬟",
  "⬡",
  "⬢",
];

// Load config from file
function loadConfig(): Config | null {
  try {
    const data = fs.readFileSync(CONFIG_FILE, "utf8");
    const fileConfig = JSON.parse(data);

    // In add-on mode, override HA connection with environment variables
    if (ADDON_MODE) {
      return {
        ...fileConfig,
        haUrl: process.env.HA_URL!,
        haToken: process.env.HA_TOKEN!,
      };
    }

    return fileConfig;
  } catch (e) {
    // In add-on mode, return minimal config with HA connection from env
    if (ADDON_MODE) {
      return {
        haUrl: process.env.HA_URL!,
        haToken: process.env.HA_TOKEN!,
      };
    }
    return null;
  }
}

// Save config to file
function saveConfig(cfg: Config): void {
  // In add-on mode, don't save HA credentials (they come from Supervisor)
  const toSave = ADDON_MODE
    ? { ...cfg, haUrl: undefined, haToken: undefined }
    : cfg;
  fs.writeFileSync(CONFIG_FILE, JSON.stringify(toSave, null, 2), "utf8");
}

// Get current config
let config = loadConfig();

// Build legend from config - calendarIds should match the calendars used for events
function buildLegend(calendarIds: string[]): LegendItem[] {
  if (config?.showLegend === false || calendarIds.length === 0) {
    return [];
  }

  const icons = config?.calendarIcons || {};
  const names = config?.calendarNames || {};

  return calendarIds.map((entityId, index) => ({
    icon: icons[entityId] || CALENDAR_ICONS[index % CALENDAR_ICONS.length],
    name:
      names[entityId] ||
      entityId
        .replace("calendar.", "")
        .replace(/_/g, " ")
        .replace(/\b\w/g, (l) => l.toUpperCase()),
  }));
}

// French translations
const i18n = {
  title: "EPCAL",
  subtitle: "Calendrier E-Paper",
  statusConnected: "Connecté à Home Assistant",
  statusNotConnected: "Non connecté à Home Assistant",
  statusNotConfigured: "Home Assistant non configuré",
  previewTitle: "Aperçu du calendrier",
  previewInfo: "984 × 1304 pixels (taille de l'écran e-paper)",
  previewAlt: "Aperçu du calendrier",
  endpointsTitle: "Points d'accès API (pour ESP32)",
  endpointCheck: "Vérifier les mises à jour (supporte ETag)",
  endpointBlack1: "Couche noire, moitié supérieure",
  endpointBlack2: "Couche noire, moitié inférieure",
  endpointRed1: "Couche rouge, moitié supérieure",
  endpointRed2: "Couche rouge, moitié inférieure",
  calendarsTitle: "Calendriers",
  calendarsSave: "Enregistrer la sélection",
  calendarsSelectAll: "Tout sélectionner",
  calendarsSelectNone: "Tout désélectionner",
  calendarsSaved: "Sélection des calendriers enregistrée",
  configTitle: "Configuration Home Assistant",
  configUrl: "URL Home Assistant",
  configUrlPlaceholder: "https://homeassistant.local:8123",
  configToken: "Token d'accès longue durée",
  configTokenPlaceholder: "Créer dans Profil → Tokens d'accès longue durée",
  configSave: "Enregistrer",
  configTest: "Tester la connexion",
  configSuccess: "Configuration enregistrée avec succès",
  configError: "Erreur de connexion à Home Assistant",
};

// Home Assistant API helper
async function haFetch(endpoint: string): Promise<any> {
  if (!config) {
    throw new Error("Home Assistant not configured");
  }
  const response = await fetch(`${config.haUrl}${endpoint}`, {
    headers: {
      Authorization: `Bearer ${config.haToken}`,
      "Content-Type": "application/json",
    },
  });
  if (!response.ok) {
    throw new Error(`HA API error: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

// Check if Home Assistant is reachable
async function checkHAConnection(): Promise<boolean> {
  if (!config) return false;
  try {
    await haFetch("/api/");
    return true;
  } catch (e) {
    console.error("Failed to connect to Home Assistant:", e);
    return false;
  }
}

// Fetch available calendars from Home Assistant
async function fetchCalendars(): Promise<
  { entity_id: string; name: string }[]
> {
  try {
    const calendars = await haFetch("/api/calendars");
    return calendars;
  } catch (e) {
    console.error("Error fetching calendars:", e);
    return [];
  }
}

// Fetch available weather entities from Home Assistant
async function fetchWeatherEntities(): Promise<
  { entity_id: string; name: string }[]
> {
  try {
    const states = await haFetch("/api/states");
    return states
      .filter((s: any) => s.entity_id.startsWith("weather."))
      .map((s: any) => ({
        entity_id: s.entity_id,
        name: s.attributes.friendly_name || s.entity_id,
      }));
  } catch (e) {
    console.error("Error fetching weather entities:", e);
    return [];
  }
}

// Auto-detect collection types by analyzing event titles from collection calendars
async function fetchCollectionTypesFromHA(): Promise<
  Array<{ name: string; icon: string }>
> {
  if (!config?.collectionCalendars || config.collectionCalendars.length === 0) {
    return [];
  }

  try {
    // Default icon mapping for common collection type keywords
    const typeKeywords: Array<{
      keywords: string[];
      name: string;
      icon: string;
    }> = [
      {
        keywords: ["garbage", "trash", "waste", "déchet", "ordure", "poubelle"],
        name: "Garbage",
        icon: "🗑️",
      },
      {
        keywords: ["recycling", "recycle", "recyclage", "récupération"],
        name: "Recycling",
        icon: "♻️",
      },
      {
        keywords: ["compost", "organic", "organique", "food waste"],
        name: "Compost",
        icon: "🍂",
      },
      {
        keywords: ["yard", "green", "vert", "garden"],
        name: "Yard Waste",
        icon: "🌿",
      },
      {
        keywords: ["glass", "verre"],
        name: "Glass",
        icon: "🫙",
      },
      {
        keywords: ["paper", "papier"],
        name: "Paper",
        icon: "📄",
      },
      {
        keywords: ["cardboard", "carton"],
        name: "Cardboard",
        icon: "📦",
      },
    ];

    // Fetch recent events from collection calendars to analyze titles
    const start = new Date();
    const end = new Date();
    end.setMonth(end.getMonth() + 2); // Look ahead 2 months

    const detectedTypes = new Set<string>();
    const typeMap = new Map<string, { name: string; icon: string }>();

    for (const calendarId of config.collectionCalendars) {
      try {
        const startStr = start.toISOString();
        const endStr = end.toISOString();
        const events: HAEvent[] = await haFetch(
          `/api/calendars/${calendarId}?start=${startStr}&end=${endStr}`,
        );

        // Analyze event titles to detect collection types
        events.forEach((event) => {
          if (!event.summary) return;

          const titleLower = event.summary.toLowerCase();

          // Check each type's keywords against the title
          for (const typeInfo of typeKeywords) {
            if (typeInfo.keywords.some((kw) => titleLower.includes(kw))) {
              if (!detectedTypes.has(typeInfo.name)) {
                detectedTypes.add(typeInfo.name);
                typeMap.set(typeInfo.name, {
                  name: typeInfo.name,
                  icon: typeInfo.icon,
                });
              }
            }
          }
        });
      } catch (e) {
        console.error(
          `Error fetching events from ${calendarId} for type detection:`,
          e,
        );
      }
    }

    // Convert to array
    return Array.from(typeMap.values());
  } catch (e) {
    console.error("Error detecting collection types:", e);
    return [];
  }
}

// Fetch binary sensor indicators for display
async function fetchIndicators(): Promise<IndicatorData[]> {
  if (!config?.displayIndicators || config.displayIndicators.length === 0) {
    return [];
  }

  try {
    const states = await haFetch("/api/states");

    return config.displayIndicators
      .map((indicator) => {
        const entityState = states.find(
          (s: any) => s.entity_id === indicator.entityId,
        );
        if (!entityState) return null;

        const state = entityState.state as "on" | "off";
        const shouldDisplay =
          indicator.showWhen === "always" ||
          (indicator.showWhen === "on" && state === "on") ||
          (indicator.showWhen === "off" && state === "off");

        return {
          entityId: indicator.entityId,
          state,
          label: indicator.label,
          icon: indicator.icon,
          shouldDisplay,
        };
      })
      .filter((ind): ind is IndicatorData => ind !== null && ind.shouldDisplay);
  } catch (e) {
    console.error("Error fetching indicators:", e);
    return [];
  }
}

// Home Assistant event structure
interface HAEvent {
  start: { dateTime?: string; date?: string };
  end: { dateTime?: string; date?: string };
  summary: string;
  description?: string;
  location?: string;
}

// Extract timezone offset from a dateTime string like "2026-01-15T18:30:00-05:00"
function extractTimezoneOffset(dateTimeStr: string): string | null {
  const match = dateTimeStr.match(/([+-]\d{2}:\d{2})$/);
  return match ? match[1] : null;
}

// Detected event timezone (cached)
let detectedEventTimezone: string | null = null;

// Fetch events from enabled calendars only
// Returns events and the list of calendar IDs that were fetched
async function fetchAllEvents(): Promise<{
  events: CalendarEvent[];
  calendarIds: string[];
}> {
  if (!config) return { events: [], calendarIds: [] };

  // Require explicit calendar selection - no calendars = no events
  const enabledCalendars = config.enabledCalendars;
  if (!enabledCalendars || enabledCalendars.length === 0) {
    return { events: [], calendarIds: [] };
  }

  try {
    const calendars = await fetchCalendars();
    const weeks = 6; // Fetch 6 weeks of events
    const start = startOfWeek(new Date());
    const end = addWeeks(start, weeks);

    const allEvents: CalendarEvent[] = [];

    // Filter to enabled calendars, plus any collection calendars (even if not enabled for display)
    const collectionCalendars = config.collectionCalendars || [];
    const calendarsToFetch = calendars.filter(
      (c) =>
        enabledCalendars.includes(c.entity_id) ||
        collectionCalendars.includes(c.entity_id),
    );

    // Ensure all calendars have icons assigned
    let configChanged = false;
    const calendarIcons = config.calendarIcons || {};
    let nextIconIndex = Object.keys(calendarIcons).length;

    for (const cal of calendarsToFetch) {
      if (!calendarIcons[cal.entity_id]) {
        calendarIcons[cal.entity_id] =
          CALENDAR_ICONS[nextIconIndex % CALENDAR_ICONS.length];
        nextIconIndex++;
        configChanged = true;
      }
    }

    if (configChanged) {
      config.calendarIcons = calendarIcons;
      saveConfig(config);
    }

    for (const cal of calendarsToFetch) {
      try {
        const startStr = start.toISOString();
        const endStr = end.toISOString();
        const events: HAEvent[] = await haFetch(
          `/api/calendars/${cal.entity_id}?start=${startStr}&end=${endStr}`,
        );

        events.forEach((item, index) => {
          if (item.start && item.summary) {
            const isAllDay = !item.start.dateTime;

            // Detect timezone from timed events
            if (!isAllDay && item.start.dateTime && !detectedEventTimezone) {
              detectedEventTimezone = extractTimezoneOffset(
                item.start.dateTime,
              );
            }

            let startDate: Date;
            let endDate: Date;

            if (isAllDay) {
              // All-day events: end date from HA is exclusive, subtract 1 day for inclusive end
              startDate = new Date(item.start.date + "T00:00:00");
              const endDateStr = item.end?.date || item.start.date;
              const exclusiveEnd = new Date(endDateStr + "T00:00:00");
              endDate = new Date(exclusiveEnd.getTime() - 24 * 60 * 60 * 1000);
            } else {
              startDate = new Date(item.start.dateTime!);
              endDate = item.end?.dateTime
                ? new Date(item.end.dateTime)
                : startDate;
            }

            allEvents.push({
              id: `${cal.entity_id}-${index}`,
              title: item.summary,
              start: startDate,
              end: endDate,
              allDay: isAllDay,
              calendarIcon: calendarIcons[cal.entity_id],
              calendarId: cal.entity_id,
            });
          }
        });
      } catch (e) {
        console.error(`Error fetching events from ${cal.entity_id}:`, e);
      }
    }

    return {
      events: allEvents,
      calendarIds: calendarsToFetch.map((c) => c.entity_id),
    };
  } catch (e) {
    console.error("Error fetching events:", e);
    return { events: [], calendarIds: [] };
  }
}

app.get("/", async (req, res) => {
  const isConfigured = !!config;
  const isConnected = isConfigured ? await checkHAConnection() : false;
  const calendars = isConnected ? await fetchCalendars() : [];
  const weatherEntities = isConnected ? await fetchWeatherEntities() : [];

  // Fetch binary sensors for indicators configuration
  const binarySensors = isConnected
    ? (await haFetch("/api/states"))
        .filter((s: any) => s.entity_id.startsWith("binary_sensor."))
        .map((s: any) => ({
          entity_id: s.entity_id,
          name: s.attributes.friendly_name || s.entity_id,
        }))
    : [];

  const message = req.query.message as string | undefined;
  const error = req.query.error as string | undefined;

  // Fetch events to detect timezone (if any calendars are enabled)
  if (isConnected && config?.enabledCalendars?.length) {
    await fetchAllEvents();
  }

  // Check timezone mismatch
  const serverTz = getServerTimezoneOffset();
  const serverTzName = getServerTimezoneName();
  const eventTz = detectedEventTimezone;
  const tzMismatch = eventTz && eventTz !== serverTz;

  const html = `<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${i18n.title} - ${i18n.subtitle}</title>
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      max-width: 1200px;
      margin: 0 auto;
      padding: 20px;
      background: #f5f5f5;
    }
    h1 { color: #333; margin-bottom: 10px; }
    .subtitle { color: #666; margin-bottom: 30px; }
    .status {
      padding: 12px 20px;
      border-radius: 8px;
      margin-bottom: 20px;
      display: inline-flex;
      align-items: center;
      gap: 10px;
    }
    .status.connected { background: #d4edda; color: #155724; }
    .status.disconnected { background: #f8d7da; color: #721c24; }
    .status.not-configured { background: #fff3cd; color: #856404; }
    .status-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
    }
    .status.connected .status-dot { background: #28a745; }
    .status.disconnected .status-dot { background: #dc3545; }
    .status.not-configured .status-dot { background: #ffc107; }
    .message {
      padding: 12px 20px;
      border-radius: 8px;
      margin-bottom: 20px;
    }
    .message.success { background: #d4edda; color: #155724; }
    .message.error { background: #f8d7da; color: #721c24; }
    .message.warning { background: #fff3cd; color: #856404; }
    .timezone-info {
      font-size: 13px;
      color: #666;
      margin-left: 15px;
    }
    .section {
      background: white;
      padding: 20px;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      margin-bottom: 20px;
    }
    .section h2 { font-size: 16px; margin-bottom: 15px; color: #333; margin-top: 0; }
    .preview-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 15px;
    }
    .preview-title { font-size: 18px; font-weight: 600; color: #333; }
    .preview-info { color: #666; font-size: 14px; }
    .preview-img {
      max-width: 100%;
      height: auto;
      border: 1px solid #ddd;
      border-radius: 4px;
    }
    .form-group {
      margin-bottom: 15px;
    }
    .form-group label {
      display: block;
      margin-bottom: 5px;
      font-weight: 500;
      color: #333;
    }
    .form-group input {
      width: 100%;
      padding: 10px 12px;
      border: 1px solid #ddd;
      border-radius: 6px;
      font-size: 14px;
    }
    .form-group input:focus {
      outline: none;
      border-color: #4285f4;
      box-shadow: 0 0 0 2px rgba(66, 133, 244, 0.2);
    }
    .form-group small {
      display: block;
      margin-top: 5px;
      color: #666;
      font-size: 12px;
    }
    .btn {
      display: inline-block;
      padding: 10px 20px;
      border: none;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      text-decoration: none;
      transition: background 0.2s;
    }
    .btn-primary {
      background: #4285f4;
      color: white;
    }
    .btn-primary:hover { background: #3367d6; }
    .btn-secondary {
      background: #6c757d;
      color: white;
      margin-left: 10px;
    }
    .btn-secondary:hover { background: #5a6268; }
    .endpoint-list { list-style: none; padding: 0; margin: 0; }
    .endpoint-list li {
      padding: 8px 0;
      border-bottom: 1px solid #eee;
      font-family: monospace;
      font-size: 14px;
    }
    .endpoint-list li:last-child { border-bottom: none; }
    .endpoint-list a { color: #4285f4; text-decoration: none; }
    .endpoint-list a:hover { text-decoration: underline; }
    .endpoint-desc { color: #666; font-family: sans-serif; margin-left: 10px; }
    .calendar-list { list-style: none; padding: 0; margin: 0; }
    .calendar-list li {
      padding: 8px 12px;
      border-bottom: 1px solid #eee;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .calendar-list li:last-child { border-bottom: none; }
    .calendar-list input[type="checkbox"] {
      width: 18px;
      height: 18px;
      cursor: pointer;
    }
    .calendar-list label {
      display: flex;
      align-items: center;
      gap: 10px;
      cursor: pointer;
      flex: 1;
    }
    .calendar-icon-select {
      width: 40px;
      padding: 4px;
      font-size: 16px;
      text-align: center;
      border: 1px solid #ddd;
      border-radius: 4px;
      cursor: pointer;
    }
    .calendar-name-input {
      width: 120px;
      padding: 4px 8px;
      font-size: 14px;
      border: 1px solid #ddd;
      border-radius: 4px;
    }
    .calendar-name-input::placeholder {
      color: #aaa;
      font-style: italic;
    }
    .calendar-order-buttons {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .calendar-order-buttons button {
      padding: 0 6px;
      font-size: 10px;
      line-height: 14px;
      background: #e9ecef;
      border: 1px solid #ddd;
      border-radius: 3px;
      cursor: pointer;
    }
    .calendar-order-buttons button:hover {
      background: #dee2e6;
    }
    .calendar-order-buttons button:disabled {
      opacity: 0.3;
      cursor: not-allowed;
    }
    .calendar-name { font-weight: 500; }
    .calendar-id { color: #666; font-size: 12px; font-family: monospace; }
    .calendar-actions {
      display: flex;
      gap: 10px;
      margin-bottom: 15px;
    }
    .btn-small {
      padding: 6px 12px;
      font-size: 12px;
      background: #e9ecef;
      color: #333;
      border: 1px solid #ddd;
    }
    .btn-small:hover { background: #dee2e6; }
    .layout-options {
      display: flex;
      gap: 15px;
      margin-bottom: 15px;
    }
    .layout-option {
      flex: 1;
      padding: 15px;
      border: 2px solid #ddd;
      border-radius: 8px;
      cursor: pointer;
      display: flex;
      flex-direction: column;
      gap: 5px;
      transition: border-color 0.2s, background 0.2s;
    }
    .layout-option:hover { border-color: #4285f4; background: #f8f9fa; }
    .layout-option.selected { border-color: #4285f4; background: #e8f0fe; }
    .layout-option:focus-within { outline: 2px solid #4285f4; outline-offset: 2px; }
    .layout-option input { position: absolute; opacity: 0; pointer-events: none; }
    .layout-label { font-weight: 600; color: #333; }
    .layout-desc { font-size: 13px; color: #666; }
    .layout-checkbox {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 15px 0;
      font-size: 14px;
      color: #333;
    }
    .layout-checkbox input[type="checkbox"] {
      width: 18px;
      height: 18px;
      cursor: pointer;
    }
    .collapsible {
      background: white;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      margin-bottom: 20px;
    }
    .collapsible summary {
      padding: 15px 20px;
      cursor: pointer;
      font-weight: 600;
      color: #333;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .collapsible summary::-webkit-details-marker { display: none; }
    .collapsible summary::before {
      content: "▶";
      font-size: 12px;
      transition: transform 0.2s;
    }
    .collapsible[open] summary::before {
      transform: rotate(90deg);
    }
    .collapsible-content {
      padding: 0 20px 20px 20px;
    }
    .two-columns {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
    }
    @media (max-width: 768px) {
      .two-columns { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <h1>${i18n.title}</h1>
  <p class="subtitle">${i18n.subtitle}</p>

  ${message ? `<div class="message success">${message}</div>` : ""}
  ${error ? `<div class="message error">${error}</div>` : ""}

  <div class="status ${isConnected ? "connected" : isConfigured ? "disconnected" : "not-configured"}">
    <span class="status-dot"></span>
    ${isConnected ? i18n.statusConnected : isConfigured ? i18n.statusNotConnected : i18n.statusNotConfigured}
    ${isConnected ? `<span class="timezone-info">Heures affichées en ${serverTzName}</span>` : ""}
  </div>

  ${
    tzMismatch
      ? `
  <div class="message warning">
    ⚠️ Les événements du calendrier sont en fuseau horaire ${eventTz}, mais le serveur est en ${serverTz} (${serverTzName}). Les heures affichées pourraient être incorrectes.
  </div>
  `
      : ""
  }

  ${
    isConnected &&
    (!config?.enabledCalendars || config.enabledCalendars.length === 0)
      ? `
  <div class="message warning">
    ⚠️ Aucun calendrier n'est activé. Sélectionnez au moins un calendrier ci-dessous pour afficher des événements.
  </div>
  `
      : ""
  }

  ${
    ADDON_MODE
      ? `
  <!-- Add-on mode: HA connection is automatic -->
  ${
    weatherEntities.length > 0
      ? `
  <details class="collapsible">
    <summary>Météo</summary>
    <div class="collapsible-content">
      <form action="/weather" method="POST">
        <div class="form-group">
          <label for="weather-entity">Entité météo pour les prévisions:</label>
          <select name="weatherEntity" id="weather-entity" class="form-control">
            <option value="">-- Aucune --</option>
            ${weatherEntities
              .map(
                (w) => `
              <option value="${w.entity_id}" ${config?.weatherEntity === w.entity_id ? "selected" : ""}>
                ${w.name} (${w.entity_id})
              </option>
            `,
              )
              .join("")}
          </select>
        </div>
        <button type="submit" class="btn btn-primary">Enregistrer</button>
      </form>
    </div>
  </details>
  `
      : ""
  }
  `
      : `
  <!-- Standalone mode: manual HA configuration -->
  <details class="collapsible" ${isConnected ? "" : "open"}>
    <summary>${i18n.configTitle}</summary>
    <div class="collapsible-content">
      <form action="/config" method="POST">
        <div class="form-group">
          <label for="haUrl">${i18n.configUrl}</label>
          <input type="url" id="haUrl" name="haUrl"
                 placeholder="${i18n.configUrlPlaceholder}"
                 value="${config?.haUrl || ""}" required>
        </div>
        <div class="form-group">
          <label for="haToken">${i18n.configToken}</label>
          <input type="password" id="haToken" name="haToken"
                 placeholder="${i18n.configTokenPlaceholder}"
                 value="${config?.haToken || ""}" required>
          <small>Créer dans Home Assistant: Profil → Tokens d'accès longue durée</small>
        </div>
        ${
          weatherEntities.length > 0
            ? `
        <div class="form-group">
          <label for="weather-entity">Entité météo pour les prévisions:</label>
          <select name="weatherEntity" id="weather-entity" class="form-control">
            <option value="">-- Aucune --</option>
            ${weatherEntities
              .map(
                (w) => `
              <option value="${w.entity_id}" ${config?.weatherEntity === w.entity_id ? "selected" : ""}>
                ${w.name} (${w.entity_id})
              </option>
            `,
              )
              .join("")}
          </select>
        </div>
        `
            : ""
        }
        <button type="submit" class="btn btn-primary">${i18n.configSave}</button>
      </form>
    </div>
  </details>
  `
  }

  ${
    isConnected
      ? `
  <div class="section">
    <div class="preview-header">
      <span class="preview-title">${i18n.previewTitle}</span>
      <span class="preview-info">${i18n.previewInfo}</span>
    </div>
    <img src="/calendar/preview" alt="${i18n.previewAlt}" class="preview-img">
    <div style="margin-top: 10px; text-align: right;">
      <a href="/debug" style="color: #666; font-size: 14px;">Debug previews →</a>
    </div>
  </div>
  `
      : ""
  }

  ${
    isConnected
      ? `
  <div class="section">
    <h2>Disposition</h2>
    <form action="/layout" method="POST">
      <div class="layout-options">
        ${LAYOUT_OPTIONS.map(
          (opt) => `
          <label class="layout-option ${(config?.layout || "landscape") === opt.value ? "selected" : ""}">
            <input type="radio" name="layout" value="${opt.value}" ${(config?.layout || "landscape") === opt.value ? "checked" : ""}>
            <span class="layout-label">${opt.label}</span>
            <span class="layout-desc">${opt.description}</span>
          </label>
        `,
        ).join("")}
      </div>
      <label class="layout-checkbox">
        <input type="checkbox" name="showLegend" value="true" ${config?.showLegend !== false ? "checked" : ""}>
        Afficher la légende des calendriers
      </label>
      <button type="submit" class="btn btn-primary">Enregistrer</button>
    </form>
    <script>
      document.querySelectorAll('.layout-option input').forEach(radio => {
        radio.addEventListener('change', () => {
          document.querySelectorAll('.layout-option').forEach(opt => opt.classList.remove('selected'));
          radio.closest('.layout-option').classList.add('selected');
        });
      });
    </script>
  </div>
  `
      : ""
  }


  ${
    calendars.length > 0
      ? `
  <div class="section">
    <h2>${i18n.calendarsTitle}</h2>
    <form action="/calendars" method="POST" id="calendars-form">
      <div class="calendar-actions">
        <button type="button" onclick="toggleAll(true)" class="btn btn-small">${i18n.calendarsSelectAll}</button>
        <button type="button" onclick="toggleAll(false)" class="btn btn-small">${i18n.calendarsSelectNone}</button>
      </div>
      <ul class="calendar-list" id="calendar-list">
        ${(() => {
          // Sort calendars: enabled ones first in saved order, then others alphabetically
          const savedOrder = config?.enabledCalendars || [];
          const sortedCalendars = [...calendars].sort((a, b) => {
            const aIndex = savedOrder.indexOf(a.entity_id);
            const bIndex = savedOrder.indexOf(b.entity_id);
            if (aIndex !== -1 && bIndex !== -1) return aIndex - bIndex;
            if (aIndex !== -1) return -1;
            if (bIndex !== -1) return 1;
            return a.name.localeCompare(b.name);
          });
          return sortedCalendars
            .map((c, index) => {
              const isEnabled =
                config?.enabledCalendars?.includes(c.entity_id) || false;
              const currentIcon =
                config?.calendarIcons?.[c.entity_id] || CALENDAR_ICONS[0];
              const currentName = config?.calendarNames?.[c.entity_id] || "";
              const placeholder = c.entity_id
                .replace("calendar.", "")
                .replace(/_/g, " ")
                .replace(/\b\w/g, (l) => l.toUpperCase());
              return `
            <li data-entity-id="${c.entity_id}">
              <div class="calendar-order-buttons">
                <button type="button" onclick="moveCalendar(this, -1)" title="Monter">▲</button>
                <button type="button" onclick="moveCalendar(this, 1)" title="Descendre">▼</button>
              </div>
              <input type="checkbox" name="calendars" value="${c.entity_id}" id="cal-${c.entity_id}" ${isEnabled ? "checked" : ""}>
              <select name="icon-${c.entity_id}" class="calendar-icon-select" title="Icône">
                ${CALENDAR_ICONS.map((icon) => `<option value="${icon}" ${icon === currentIcon ? "selected" : ""}>${icon}</option>`).join("")}
              </select>
              <input type="text" name="name-${c.entity_id}" class="calendar-name-input" placeholder="${placeholder}" value="${currentName}" title="Nom affiché">
              <label for="cal-${c.entity_id}">
                <span class="calendar-name">${c.name}</span>
                <span class="calendar-id">${c.entity_id}</span>
              </label>
              <input type="checkbox" name="collection-${c.entity_id}" id="collection-${c.entity_id}" ${config?.collectionCalendars?.includes(c.entity_id) ? "checked" : ""} title="Calendrier de collecte">
              <label for="collection-${c.entity_id}" style="font-size: 12px; margin-left: 5px;">📦 Collecte</label>
              <input type="hidden" name="order[]" value="${c.entity_id}">
            </li>
          `;
            })
            .join("");
        })()}
      </ul>
      <button type="submit" class="btn btn-primary">${i18n.calendarsSave}</button>
    </form>
    <script>
      function toggleAll(checked) {
        document.querySelectorAll('input[name="calendars"]').forEach(cb => cb.checked = checked);
      }
      function moveCalendar(button, direction) {
        const li = button.closest('li');
        const list = document.getElementById('calendar-list');
        const items = Array.from(list.children);
        const index = items.indexOf(li);
        const newIndex = index + direction;

        if (newIndex < 0 || newIndex >= items.length) return;

        if (direction === -1) {
          list.insertBefore(li, items[newIndex]);
        } else {
          list.insertBefore(li, items[newIndex].nextSibling);
        }

        // Update hidden order inputs
        Array.from(list.children).forEach((item, i) => {
          const orderInput = item.querySelector('input[name="order[]"]');
          if (orderInput) {
            orderInput.value = item.dataset.entityId;
          }
        });
      }
    </script>
  </div>
  `
      : ""
  }

  ${
    isConnected && (config?.collectionCalendars?.length || 0) > 0
      ? `
  <div class="section">
    <h2>Types de collecte</h2>
    <p>Configurez les types de collecte (déchets, recyclage, compost, etc.) avec leurs icônes.</p>
    <form action="/collection-types/detect" method="POST" style="display: inline-block; margin-bottom: 10px;">
      <button type="submit" class="btn btn-small">🔍 Détecter automatiquement</button>
    </form>
    <form action="/collection-types" method="POST" id="collection-types-form">
      <div id="collection-types-list" style="display: flex; flex-direction: column; gap: 10px;">
        ${(config?.collectionTypes || [])
          .map(
            (type, index) =>
              `<div class="collection-type-item" style="display: flex; gap: 10px; align-items: center;">
          <input type="text" name="name-${index}" placeholder="Nom (ex: Garbage, Recycling)" value="${type.name}" required style="flex: 1;">
          <input type="text" name="icon-${index}" placeholder="Icône (emoji)" value="${type.icon}" maxlength="2" required style="width: 80px;">
          <button type="button" onclick="this.parentElement.remove()" class="btn btn-small">Supprimer</button>
        </div>`,
          )
          .join("")}
      </div>
      <button type="button" onclick="addCollectionTypeRow()" class="btn btn-small" style="margin-top: 10px;">Ajouter un type</button>
      <button type="submit" class="btn btn-primary" style="margin-top: 10px;">Enregistrer les types de collecte</button>
    </form>
    <script>
      function addCollectionTypeRow() {
        const list = document.getElementById('collection-types-list');
        const index = list.children.length;
        const div = document.createElement('div');
        div.className = 'collection-type-item';
        div.style.cssText = 'display: flex; gap: 10px; align-items: center;';
        div.innerHTML = '<input type="text" name="name-' + index + '" placeholder="Nom (ex: Garbage, Recycling)" required style="flex: 1;">' +
          '<input type="text" name="icon-' + index + '" placeholder="Icône (emoji)" maxlength="2" required style="width: 80px;">' +
          '<button type="button" onclick="this.parentElement.remove()" class="btn btn-small">Supprimer</button>';
        list.appendChild(div);
      }
    </script>
  </div>
  `
      : ""
  }

  ${
    isConnected
      ? `
  <div class="section">
    <h2>Indicateurs & Rappels</h2>
    <p>Configurez des indicateurs de capteurs binaires à afficher dans la vue 6 jours.</p>
    <form action="/indicators" method="POST" id="indicators-form">
      <div id="indicators-list" style="display: flex; flex-direction: column; gap: 10px;">
        ${(config?.displayIndicators || [])
          .map(
            (ind, index) =>
              `<div class="indicator-item" style="display: flex; gap: 10px; align-items: center;">
          <select name="entityId-${index}" required style="flex: 1;">
            <option value="">Sélectionner un capteur binaire...</option>
            ${binarySensors
              .map(
                (s: any) =>
                  `<option value="${s.entity_id}"${s.entity_id === ind.entityId ? " selected" : ""}>${s.name}</option>`,
              )
              .join("")}
          </select>
          <input type="text" name="label-${index}" placeholder="Label" value="${ind.label}" required style="width: 120px;">
          <input type="text" name="icon-${index}" placeholder="Icône" value="${ind.icon}" maxlength="2" required style="width: 60px;">
          <select name="showWhen-${index}" required style="width: 100px;">
            <option value="on"${ind.showWhen === "on" ? " selected" : ""}>Quand ON</option>
            <option value="off"${ind.showWhen === "off" ? " selected" : ""}>Quand OFF</option>
            <option value="always"${ind.showWhen === "always" ? " selected" : ""}>Toujours</option>
          </select>
          <button type="button" onclick="this.parentElement.remove()" class="btn btn-small">Supprimer</button>
        </div>`,
          )
          .join("")}
      </div>
      <button type="button" onclick="addIndicatorRow()" class="btn btn-small" style="margin-top: 10px;">Ajouter un indicateur</button>
      <button type="submit" class="btn btn-primary" style="margin-top: 10px;">Enregistrer les indicateurs</button>
    </form>
    <script>
      const sensorOptions = ${JSON.stringify(binarySensors.map((s: any) => `<option value="${s.entity_id}">${s.name}</option>`).join(""))};

      function addIndicatorRow() {
        const list = document.getElementById('indicators-list');
        const index = list.children.length;
        const div = document.createElement('div');
        div.className = 'indicator-item';
        div.style.cssText = 'display: flex; gap: 10px; align-items: center;';

        const html = '<select name="entityId-' + index + '" required style="flex: 1;"><option value="">Sélectionner un capteur binaire...</option>' + sensorOptions + '</select>' +
          '<input type="text" name="label-' + index + '" placeholder="Label" required style="width: 120px;">' +
          '<input type="text" name="icon-' + index + '" placeholder="Icône" maxlength="2" required style="width: 60px;">' +
          '<select name="showWhen-' + index + '" required style="width: 100px;"><option value="on">Quand ON</option><option value="off">Quand OFF</option><option value="always">Toujours</option></select>' +
          '<button type="button" onclick="this.parentElement.remove()" class="btn btn-small">Supprimer</button>';

        div.innerHTML = html;
        list.appendChild(div);
      }
    </script>
  </div>
  `
      : ""
  }

  <div class="section">
    <h2>${i18n.endpointsTitle}</h2>
    <ul class="endpoint-list">
      <li><a href="/calendar/check">/calendar/check</a> <span class="endpoint-desc">- ${i18n.endpointCheck}</span></li>
      <li><a href="/calendar/black1">/calendar/black1</a> <span class="endpoint-desc">- ${i18n.endpointBlack1}</span></li>
      <li><a href="/calendar/black2">/calendar/black2</a> <span class="endpoint-desc">- ${i18n.endpointBlack2}</span></li>
      <li><a href="/calendar/red1">/calendar/red1</a> <span class="endpoint-desc">- ${i18n.endpointRed1}</span></li>
      <li><a href="/calendar/red2">/calendar/red2</a> <span class="endpoint-desc">- ${i18n.endpointRed2}</span></li>
      <li><a href="/calendar/icon-test">/calendar/icon-test</a> <span class="endpoint-desc">- Test d'alignement des icônes</span></li>
    </ul>
  </div>
  <script>
    // Clean up URL after showing message
    if (window.location.search.includes('message=') || window.location.search.includes('error=')) {
      history.replaceState(null, '', window.location.pathname);
    }
  </script>
</body>
</html>`;

  res.setHeader("Content-Type", "text/html");
  res.send(html);
});

// Handle config form submission
app.post("/config", async (req, res) => {
  const { haUrl, haToken, weatherEntity } = req.body;

  if (!haUrl || !haToken) {
    return res.redirect("/?error=" + encodeURIComponent("URL et token requis"));
  }

  // Test the connection before saving
  const newConfig: Config = {
    ...config, // Preserve existing settings (calendars, layout, etc.)
    haUrl: haUrl.replace(/\/$/, ""),
    haToken,
    weatherEntity: weatherEntity || undefined,
  };

  try {
    const response = await fetch(`${newConfig.haUrl}/api/`, {
      headers: {
        Authorization: `Bearer ${newConfig.haToken}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    // Connection successful, save config
    saveConfig(newConfig);
    config = newConfig;

    // Clear render cache
    cachedRender = null;
    cacheTimestamp = null;

    res.redirect("/?message=" + encodeURIComponent(i18n.configSuccess));
  } catch (e) {
    console.error("Config test failed:", e);
    res.redirect(
      "/?error=" +
        encodeURIComponent(i18n.configError + ": " + (e as Error).message),
    );
  }
});

// Handle layout selection form submission
app.post("/layout", async (req, res) => {
  if (!config) {
    return res.redirect(
      "/?error=" + encodeURIComponent("Configuration requise"),
    );
  }

  const layout = req.body.layout as "portrait" | "landscape";
  if (layout && (layout === "portrait" || layout === "landscape")) {
    config.layout = layout;
  }

  // Checkbox: present in body if checked, absent if unchecked
  config.showLegend = req.body.showLegend === "true";

  saveConfig(config);

  // Clear render cache to reflect changes
  cachedRender = null;
  cacheTimestamp = null;

  res.redirect("/?message=" + encodeURIComponent("Disposition enregistrée"));
});

// Handle weather entity selection (for add-on mode)
app.post("/weather", async (req, res) => {
  if (!config) {
    return res.redirect(
      "/?error=" + encodeURIComponent("Configuration requise"),
    );
  }

  config.weatherEntity = req.body.weatherEntity || undefined;
  saveConfig(config);

  // Clear render cache
  cachedRender = null;
  cacheTimestamp = null;

  res.redirect("/?message=" + encodeURIComponent("Météo enregistrée"));
});

// Handle calendar selection form submission
app.post("/calendars", async (req, res) => {
  if (!config) {
    return res.redirect(
      "/?error=" + encodeURIComponent("Configuration requise"),
    );
  }

  // Get calendar order from hidden inputs (Express parses order[] as req.body.order)
  let calendarOrder: string[] = [];
  if (req.body.order) {
    calendarOrder = Array.isArray(req.body.order)
      ? req.body.order
      : [req.body.order];
  }

  // Get selected calendars from form (can be string or array)
  let selectedCalendarsSet = new Set<string>();
  if (req.body.calendars) {
    const calendars = Array.isArray(req.body.calendars)
      ? req.body.calendars
      : [req.body.calendars];
    calendars.forEach((c: string) => selectedCalendarsSet.add(c));
  }

  // Build selected calendars in the order from the form
  const selectedCalendars = calendarOrder.filter((id) =>
    selectedCalendarsSet.has(id),
  );

  // Get icon, name, and collection calendar selections from form
  const calendarIcons: { [entityId: string]: string } =
    config.calendarIcons || {};
  const calendarNames: { [entityId: string]: string } =
    config.calendarNames || {};
  const collectionCalendars: string[] = [];

  for (const key of Object.keys(req.body)) {
    if (key.startsWith("icon-")) {
      const entityId = key.replace("icon-", "");
      calendarIcons[entityId] = req.body[key];
    } else if (key.startsWith("name-")) {
      const entityId = key.replace("name-", "");
      const name = req.body[key].trim();
      if (name) {
        calendarNames[entityId] = name;
      } else {
        delete calendarNames[entityId]; // Remove empty names
      }
    } else if (key.startsWith("collection-")) {
      const entityId = key.replace("collection-", "");
      if (req.body[key] === "on") {
        collectionCalendars.push(entityId);
      }
    }
  }

  // Update config with selected calendars, icons, names, and collection calendars
  config.enabledCalendars = selectedCalendars;
  config.calendarIcons = calendarIcons;
  config.calendarNames = calendarNames;
  config.collectionCalendars = collectionCalendars;
  saveConfig(config);

  // Clear render cache to reflect changes
  cachedRender = null;
  cacheTimestamp = null;

  res.redirect("/?message=" + encodeURIComponent(i18n.calendarsSaved));
});

// Handle indicators configuration form submission
app.post("/indicators", async (req, res) => {
  if (!config) {
    return res.redirect(
      "/?error=" + encodeURIComponent("Configuration requise"),
    );
  }

  const indicators: Config["displayIndicators"] = [];
  let index = 0;

  while (req.body[`entityId-${index}`]) {
    indicators.push({
      entityId: req.body[`entityId-${index}`],
      label: req.body[`label-${index}`],
      icon: req.body[`icon-${index}`],
      showWhen: req.body[`showWhen-${index}`] as "on" | "off" | "always",
    });
    index++;
  }

  config.displayIndicators = indicators;
  saveConfig(config);

  // Clear render cache
  cachedRender = null;
  cacheTimestamp = null;

  res.redirect("/?message=" + encodeURIComponent("Indicateurs enregistrés"));
});

// Handle collection types configuration form submission
app.post("/collection-types", async (req, res) => {
  if (!config) {
    return res.redirect(
      "/?error=" + encodeURIComponent("Configuration requise"),
    );
  }

  const collectionTypes: Config["collectionTypes"] = [];
  let index = 0;

  while (req.body[`name-${index}`]) {
    const name = req.body[`name-${index}`].trim();
    const icon = req.body[`icon-${index}`].trim();
    if (name && icon) {
      collectionTypes.push({
        name,
        icon,
      });
    }
    index++;
  }

  config.collectionTypes = collectionTypes;
  saveConfig(config);

  // Clear render cache
  cachedRender = null;
  cacheTimestamp = null;

  res.redirect(
    "/?message=" + encodeURIComponent("Types de collecte enregistrés"),
  );
});

// Auto-detect collection types from calendar events
app.post("/collection-types/detect", async (req, res) => {
  if (!config) {
    return res.redirect(
      "/?error=" + encodeURIComponent("Configuration requise"),
    );
  }

  // Check if collection calendars are configured
  if (!config.collectionCalendars || config.collectionCalendars.length === 0) {
    return res.redirect(
      "/?error=" +
        encodeURIComponent(
          "Aucun calendrier de collecte configuré. Cochez d'abord des calendriers comme calendriers de collecte.",
        ),
    );
  }

  try {
    console.log("Starting collection type auto-detection...");
    const detectedTypes = await fetchCollectionTypesFromHA();
    console.log("Detected types:", detectedTypes);

    // Merge with existing types (don't overwrite user customizations)
    const existingTypes = config.collectionTypes || [];
    const existingNames = new Set(
      existingTypes.map((t) => t.name.toLowerCase()),
    );

    let addedCount = 0;
    // Add newly detected types that don't exist yet
    for (const type of detectedTypes) {
      if (!existingNames.has(type.name.toLowerCase())) {
        existingTypes.push(type);
        addedCount++;
      }
    }

    console.log(`Added ${addedCount} new types`);
    config.collectionTypes = existingTypes;
    saveConfig(config);

    // Clear render cache
    cachedRender = null;
    cacheTimestamp = null;

    const message =
      addedCount > 0
        ? addedCount + " type(s) detecte(s) et ajoute(s)"
        : "Aucun nouveau type detecte";
    res.redirect("/?message=" + encodeURIComponent(message));
  } catch (e: any) {
    console.error("Error auto-detecting collection types:", e);
    const errorMsg = e.message || "Erreur lors de la detection des types";
    res.redirect("/?error=" + encodeURIComponent(errorMsg));
  }
});

// Debug endpoint to list collection calendar event titles
app.get("/collection-events", async (_req, res) => {
  if (!config?.collectionCalendars || config.collectionCalendars.length === 0) {
    return res.json({ error: "No collection calendars configured" });
  }

  try {
    const start = new Date();
    const end = new Date();
    end.setMonth(end.getMonth() + 2);

    const eventTitles: { [calendarId: string]: string[] } = {};

    for (const calendarId of config.collectionCalendars) {
      const startStr = start.toISOString();
      const endStr = end.toISOString();
      const events: HAEvent[] = await haFetch(
        `/api/calendars/${calendarId}?start=${startStr}&end=${endStr}`,
      );
      eventTitles[calendarId] = events.map((e) => e.summary).filter(Boolean);
    }

    res.json(eventTitles);
  } catch (e: any) {
    console.error("Error:", e);
    res.status(500).json({ error: e.message });
  }
});

// Debug endpoint to list calendars
app.get("/calendars", async (_req, res) => {
  try {
    const calendars = await fetchCalendars();
    res.json(calendars);
  } catch (e) {
    console.error("Error:", e);
    res.status(500).json({ error: "Failed to fetch calendars" });
  }
});

// Debug endpoint to list events
app.get("/events", async (_req, res) => {
  try {
    const { events, calendarIds } = await fetchAllEvents();
    res.json({ events, calendarIds });
  } catch (e) {
    console.error("Error:", e);
    res.status(500).json({ error: "Failed to fetch events" });
  }
});

app.listen(port, () => {
  console.log(`EPCAL server listening on port ${port}`);
  if (config) {
    console.log(`Home Assistant configured: ${config.haUrl}`);
  } else {
    console.log(
      "Home Assistant not configured - visit http://localhost:" +
        port +
        " to configure",
    );
  }

  // Get local IP addresses for private networks
  const interfaces = os.networkInterfaces();
  const privateIPs: string[] = [];

  for (const name of Object.keys(interfaces)) {
    for (const iface of interfaces[name] || []) {
      if (iface.family === "IPv4" && !iface.internal) {
        if (
          iface.address.startsWith("192.168.") ||
          iface.address.startsWith("10.") ||
          iface.address.match(/^172\.(1[6-9]|2[0-9]|3[0-1])\./)
        ) {
          privateIPs.push(iface.address);
          console.log(`Found private IP: ${iface.address} on ${name}`);
        }
      }
    }
  }

  // Set up mDNS responder using multicast-dns
  // Bind to all interfaces by using INADDR_ANY and enabling multicast loopback
  const mdnsResponder = mdns({
    multicast: true,
    reuseAddr: true,
    loopback: true,
  });
  const serviceName = "EPCAL Calendar Server";
  const serviceType = "_epcal._tcp.local";
  const hostname = "epcal-server.local";

  mdnsResponder.on("query", (query: any) => {
    // Check if the query is for our service
    const isServiceQuery = query.questions.some(
      (q: any) =>
        q.name === serviceType || q.name === "_services._dns-sd._udp.local",
    );
    const isHostQuery = query.questions.some((q: any) => q.name === hostname);
    const isInstanceQuery = query.questions.some(
      (q: any) => q.name === `${serviceName}.${serviceType}`,
    );

    if (isServiceQuery || isHostQuery || isInstanceQuery) {
      const answers: any[] = [];

      // PTR record for service discovery
      if (isServiceQuery) {
        answers.push({
          name: serviceType,
          type: "PTR",
          ttl: 4500,
          data: `${serviceName}.${serviceType}`,
        });
      }

      // SRV record pointing to hostname
      if (isServiceQuery || isInstanceQuery) {
        answers.push({
          name: `${serviceName}.${serviceType}`,
          type: "SRV",
          ttl: 4500,
          data: {
            port: Number(port),
            weight: 0,
            priority: 0,
            target: hostname,
          },
        });

        // TXT record with service info
        answers.push({
          name: `${serviceName}.${serviceType}`,
          type: "TXT",
          ttl: 4500,
          data: ["version=1", "path=/calendar"],
        });
      }

      // A records for each private IP
      if (isServiceQuery || isHostQuery || isInstanceQuery) {
        for (const ip of privateIPs) {
          answers.push({
            name: hostname,
            type: "A",
            ttl: 120,
            data: ip,
          });
        }
      }

      if (answers.length > 0) {
        mdnsResponder.respond(answers);
      }
    }
  });

  // Announce the service on startup
  const announceService = () => {
    const answers: any[] = [
      {
        name: serviceType,
        type: "PTR",
        ttl: 4500,
        data: `${serviceName}.${serviceType}`,
      },
      {
        name: `${serviceName}.${serviceType}`,
        type: "SRV",
        ttl: 4500,
        data: {
          port: Number(port),
          weight: 0,
          priority: 0,
          target: hostname,
        },
      },
      {
        name: `${serviceName}.${serviceType}`,
        type: "TXT",
        ttl: 4500,
        data: ["version=1", "path=/calendar"],
      },
    ];

    for (const ip of privateIPs) {
      answers.push({
        name: hostname,
        type: "A",
        ttl: 120,
        data: ip,
      });
    }

    mdnsResponder.respond(answers);
  };

  // Announce immediately and every 30 seconds
  announceService();
  setInterval(announceService, 30000);

  console.log(`mDNS: Advertising _epcal._tcp service on port ${port}`);
  console.log(`mDNS: Available on IPs: ${privateIPs.join(", ")}`);
});

// ============================================================
// Calendar Bitmap Rendering Endpoints
// ============================================================

// Cache for rendered calendar
let cachedRender: RenderedCalendar | null = null;
let cacheTimestamp: Date | null = null;
const CACHE_TTL_MS = 60 * 1000; // Re-render every minute (for clock updates)

async function getOrRenderCalendar(): Promise<RenderedCalendar> {
  const now = new Date();

  // Check if cache is still valid
  if (
    cachedRender &&
    cacheTimestamp &&
    now.getTime() - cacheTimestamp.getTime() < CACHE_TTL_MS
  ) {
    return cachedRender;
  }

  // Fetch events, weather, and indicators, then render
  console.log("Rendering calendar...");
  const { events, calendarIds } = await fetchAllEvents();
  const legend = buildLegend(calendarIds);
  const weather = await getWeatherForRendering();
  const indicators = await fetchIndicators();

  // Debug: Log collection calendar setup
  console.log("Collection calendars:", config?.collectionCalendars);
  console.log("Collection types:", config?.collectionTypes);
  console.log("Total events:", events.length);
  const collectionEvents = events.filter(
    (e) =>
      config?.collectionCalendars?.includes(e.calendarId || "") && e.allDay,
  );
  console.log(
    "Collection events found:",
    collectionEvents.length,
    collectionEvents.map((e) => ({
      title: e.title,
      start: e.start.toDateString(),
      calendarId: e.calendarId,
    })),
  );

  cachedRender = await renderCalendar(
    events,
    now,
    config?.layout || "landscape",
    legend,
    weather,
    indicators,
    config?.collectionCalendars || [],
    config?.collectionTypes || [],
  );
  cacheTimestamp = now;
  console.log(
    `Rendered calendar with ${events.length} events, ${calendarIds.length} calendars, ${weather.length} weather days, ${indicators.length} indicators, ETag: ${cachedRender.etag}`,
  );

  return cachedRender;
}

// Serve calendar preview as PNG (for debugging)
// Debug modes:
//   ?debug=true     - Add dummy events for testing overflow
//   ?debug=empty    - Completely empty calendar (no events at all)
//   ?debug=no-today - No events today, but other days have events
//   ?debug=sparse   - Sparse events (some empty days, minimal upcoming)
//   ?debug=no-upcoming - Events in Today and 6-day, but nothing in À venir
app.get("/calendar/preview", async (req, res) => {
  console.log("Preview endpoint called");
  try {
    let { events, calendarIds } = await fetchAllEvents();
    const legend = buildLegend(calendarIds);
    const now = new Date();
    const debugMode = req.query.debug as string;

    console.log("Collection calendars:", config?.collectionCalendars);
    console.log("Collection types:", config?.collectionTypes);
    console.log("Total events fetched:", events.length);
    console.log("Calendar IDs in events:", [
      ...new Set(events.map((e) => e.calendarId)),
    ]);

    // Show all events from calendar.ics
    const icsEvents = events.filter((e) => e.calendarId === "calendar.ics");
    console.log("Events from calendar.ics:", icsEvents.length);
    if (icsEvents.length > 0) {
      console.log(
        "Sample ICS events:",
        icsEvents.slice(0, 5).map((e) => ({
          title: e.title,
          start: e.start.toDateString(),
          allDay: e.allDay,
          calendarId: e.calendarId,
        })),
      );
    }

    const collectionEvents = events.filter(
      (e) =>
        config?.collectionCalendars?.includes(e.calendarId || "") && e.allDay,
    );
    console.log("Collection events (filtered):", collectionEvents.length);
    if (collectionEvents.length > 0) {
      console.log(
        "Collection event details:",
        collectionEvents.map((e) => ({
          title: e.title,
          start: e.start.toDateString(),
          calendarId: e.calendarId,
        })),
      );
    }

    // Debug mode: completely empty calendar
    if (debugMode === "empty") {
      events = [];
    }

    // Debug mode: no events today, but other days have events
    if (debugMode === "no-today") {
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      const tomorrow = new Date(today.getTime() + 24 * 60 * 60 * 1000);
      const twoDaysLater = new Date(today.getTime() + 2 * 24 * 60 * 60 * 1000);
      const threeDaysLater = new Date(
        today.getTime() + 3 * 24 * 60 * 60 * 1000,
      );
      const defaultIcon =
        config?.calendarIcons?.[config?.enabledCalendars?.[0] || ""] || "●";

      events = [
        // Tomorrow has a few events
        {
          id: "no-today-1",
          title: "Réunion d'équipe",
          start: new Date(
            tomorrow.getFullYear(),
            tomorrow.getMonth(),
            tomorrow.getDate(),
            9,
            0,
          ),
          end: new Date(
            tomorrow.getFullYear(),
            tomorrow.getMonth(),
            tomorrow.getDate(),
            10,
            0,
          ),
          allDay: false,
          calendarIcon: defaultIcon,
        },
        {
          id: "no-today-2",
          title: "Déjeuner",
          start: new Date(
            tomorrow.getFullYear(),
            tomorrow.getMonth(),
            tomorrow.getDate(),
            12,
            0,
          ),
          end: new Date(
            tomorrow.getFullYear(),
            tomorrow.getMonth(),
            tomorrow.getDate(),
            13,
            0,
          ),
          allDay: false,
          calendarIcon: defaultIcon,
        },
        // Day+2 has one event
        {
          id: "no-today-3",
          title: "Appel client",
          start: new Date(
            twoDaysLater.getFullYear(),
            twoDaysLater.getMonth(),
            twoDaysLater.getDate(),
            14,
            0,
          ),
          end: new Date(
            twoDaysLater.getFullYear(),
            twoDaysLater.getMonth(),
            twoDaysLater.getDate(),
            15,
            0,
          ),
          allDay: false,
          calendarIcon: defaultIcon,
        },
        // Day+3 is empty (to test empty column in 6-day view)
        // Day+4 has an event
        {
          id: "no-today-4",
          title: "Formation",
          start: new Date(
            threeDaysLater.getFullYear(),
            threeDaysLater.getMonth(),
            threeDaysLater.getDate(),
            10,
            0,
          ),
          end: new Date(
            threeDaysLater.getFullYear(),
            threeDaysLater.getMonth(),
            threeDaysLater.getDate(),
            16,
            0,
          ),
          allDay: false,
          calendarIcon: defaultIcon,
        },
      ];
    }

    // Debug mode: sparse events with empty À venir section
    if (debugMode === "sparse") {
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      const tomorrow = new Date(today.getTime() + 24 * 60 * 60 * 1000);
      const defaultIcon =
        config?.calendarIcons?.[config?.enabledCalendars?.[0] || ""] || "●";
      const secondIcon =
        config?.calendarIcons?.[config?.enabledCalendars?.[1] || ""] || "◆";

      events = [
        // Today has 2 events
        {
          id: "sparse-1",
          title: "Standup",
          start: new Date(
            today.getFullYear(),
            today.getMonth(),
            today.getDate(),
            9,
            0,
          ),
          end: new Date(
            today.getFullYear(),
            today.getMonth(),
            today.getDate(),
            9,
            30,
          ),
          allDay: false,
          calendarIcon: defaultIcon,
        },
        {
          id: "sparse-2",
          title: "Revue de code",
          start: new Date(
            today.getFullYear(),
            today.getMonth(),
            today.getDate(),
            14,
            0,
          ),
          end: new Date(
            today.getFullYear(),
            today.getMonth(),
            today.getDate(),
            15,
            0,
          ),
          allDay: false,
          calendarIcon: secondIcon,
        },
        // Tomorrow has 1 event
        {
          id: "sparse-3",
          title: "Dentiste",
          start: new Date(
            tomorrow.getFullYear(),
            tomorrow.getMonth(),
            tomorrow.getDate(),
            11,
            0,
          ),
          end: new Date(
            tomorrow.getFullYear(),
            tomorrow.getMonth(),
            tomorrow.getDate(),
            12,
            0,
          ),
          allDay: false,
          calendarIcon: defaultIcon,
        },
        // No upcoming multi-day events (À venir will be empty)
      ];
    }

    // Debug mode: no upcoming events (À venir empty)
    if (debugMode === "no-upcoming") {
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      const tomorrow = new Date(today.getTime() + 24 * 60 * 60 * 1000);
      const twoDaysLater = new Date(today.getTime() + 2 * 24 * 60 * 60 * 1000);
      const defaultIcon =
        config?.calendarIcons?.[config?.enabledCalendars?.[0] || ""] || "●";

      events = [
        // Today has events
        {
          id: "no-up-1",
          title: "Réunion quotidienne",
          start: new Date(
            today.getFullYear(),
            today.getMonth(),
            today.getDate(),
            9,
            0,
          ),
          end: new Date(
            today.getFullYear(),
            today.getMonth(),
            today.getDate(),
            9,
            30,
          ),
          allDay: false,
          calendarIcon: defaultIcon,
        },
        {
          id: "no-up-2",
          title: "Déjeuner d'équipe",
          start: new Date(
            today.getFullYear(),
            today.getMonth(),
            today.getDate(),
            12,
            0,
          ),
          end: new Date(
            today.getFullYear(),
            today.getMonth(),
            today.getDate(),
            13,
            0,
          ),
          allDay: false,
          calendarIcon: defaultIcon,
        },
        {
          id: "no-up-3",
          title: "Session de travail",
          start: new Date(
            today.getFullYear(),
            today.getMonth(),
            today.getDate(),
            14,
            0,
          ),
          end: new Date(
            today.getFullYear(),
            today.getMonth(),
            today.getDate(),
            17,
            0,
          ),
          allDay: false,
          calendarIcon: defaultIcon,
        },
        // Tomorrow and day+2 have events too
        {
          id: "no-up-4",
          title: "Appel fournisseur",
          start: new Date(
            tomorrow.getFullYear(),
            tomorrow.getMonth(),
            tomorrow.getDate(),
            10,
            0,
          ),
          end: new Date(
            tomorrow.getFullYear(),
            tomorrow.getMonth(),
            tomorrow.getDate(),
            11,
            0,
          ),
          allDay: false,
          calendarIcon: defaultIcon,
        },
        {
          id: "no-up-5",
          title: "Présentation",
          start: new Date(
            twoDaysLater.getFullYear(),
            twoDaysLater.getMonth(),
            twoDaysLater.getDate(),
            15,
            0,
          ),
          end: new Date(
            twoDaysLater.getFullYear(),
            twoDaysLater.getMonth(),
            twoDaysLater.getDate(),
            16,
            0,
          ),
          allDay: false,
          calendarIcon: defaultIcon,
        },
        // No multi-day or all-day events beyond 6-day window
      ];
    }

    // Add dummy events for testing overflow
    if (debugMode === "true") {
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      const tomorrow = new Date(today.getTime() + 24 * 60 * 60 * 1000);
      const dayAfterTomorrow = new Date(
        today.getTime() + 2 * 24 * 60 * 60 * 1000,
      );
      const threeDaysLater = new Date(
        today.getTime() + 3 * 24 * 60 * 60 * 1000,
      );
      const fourDaysLater = new Date(today.getTime() + 4 * 24 * 60 * 60 * 1000);

      const dummyEvents: CalendarEvent[] = [];
      const defaultIcon =
        config?.calendarIcons?.[config?.enabledCalendars?.[0] || ""] || "●";
      const secondIcon =
        config?.calendarIcons?.[config?.enabledCalendars?.[1] || ""] || "◆";

      // Add 15 events for today to test overflow
      for (let i = 0; i < 15; i++) {
        const hour = 7 + i;
        let title = `Événement test ${i + 1}`;
        if (i === 3) {
          title =
            "Réunion stratégique avec l'ensemble des parties prenantes du projet de modernisation";
        } else if (i === 7) {
          title =
            "Conférence internationale sur les nouvelles technologies émergentes et leur impact";
        }
        dummyEvents.push({
          id: `dummy-today-${i}`,
          title,
          start: new Date(
            today.getFullYear(),
            today.getMonth(),
            today.getDate(),
            hour,
            0,
          ),
          end: new Date(
            today.getFullYear(),
            today.getMonth(),
            today.getDate(),
            hour,
            30,
          ),
          allDay: false,
          calendarIcon: defaultIcon,
        });
      }

      // All-day event for tomorrow
      dummyEvents.push({
        id: `dummy-allday-tomorrow`,
        title: "Journée de formation obligatoire",
        start: tomorrow,
        end: new Date(tomorrow.getTime() + 24 * 60 * 60 * 1000),
        allDay: true,
        calendarIcon: secondIcon,
      });

      // 3-day event starting day after tomorrow
      dummyEvents.push({
        id: `dummy-multiday`,
        title: "Conférence annuelle des développeurs",
        start: dayAfterTomorrow,
        end: new Date(dayAfterTomorrow.getTime() + 3 * 24 * 60 * 60 * 1000),
        allDay: true,
        calendarIcon: secondIcon,
      });

      // Add 15 events for 3 days from now to test overflow
      for (let i = 0; i < 15; i++) {
        const hour = 7 + i;
        let title = `Événement jour+3 #${i + 1}`;
        if (i === 2) {
          title =
            "Présentation des résultats trimestriels aux investisseurs et actionnaires";
        } else if (i === 5) {
          title =
            "Atelier de co-création avec les utilisateurs finaux du produit";
        }
        dummyEvents.push({
          id: `dummy-day3-${i}`,
          title,
          start: new Date(
            threeDaysLater.getFullYear(),
            threeDaysLater.getMonth(),
            threeDaysLater.getDate(),
            hour,
            0,
          ),
          end: new Date(
            threeDaysLater.getFullYear(),
            threeDaysLater.getMonth(),
            threeDaysLater.getDate(),
            hour,
            30,
          ),
          allDay: false,
          calendarIcon: defaultIcon,
        });
      }

      events = [...events, ...dummyEvents];
    }

    const weather = await getWeatherForRendering();
    const indicators = await fetchIndicators();

    // Filter out collection calendar events from display (they'll only show as icons)
    const collectionCalendars = config?.collectionCalendars || [];
    const visibleEvents = events.filter(
      (e) => !collectionCalendars.includes(e.calendarId || ""),
    );

    const png = await renderToPng(
      visibleEvents, // Pass filtered events for display
      now,
      config?.layout || "landscape",
      legend,
      weather,
      indicators,
      collectionCalendars,
      config?.collectionTypes || [],
      events, // Pass ALL events for collection icon matching
    );
    res.setHeader("Content-Type", "image/png");
    res.send(png);
  } catch (e) {
    console.error("Error rendering preview:", e);
    res.status(500).send("Error rendering preview");
  }
});

// Debug page showing all preview modes
app.get("/debug", (req, res) => {
  const debugModes = [
    {
      mode: "",
      label: "Normal",
      description: "Real calendar data from Home Assistant",
    },
    {
      mode: "true",
      label: "Overflow",
      description:
        "Many events to test overflow indicators and text truncation",
    },
    {
      mode: "empty",
      label: "Empty",
      description: "Completely empty calendar (no events at all)",
    },
    {
      mode: "no-today",
      label: "No Today",
      description: "No events today, but other days have events",
    },
    {
      mode: "sparse",
      label: "Sparse",
      description: "Few events, empty À venir section",
    },
    {
      mode: "no-upcoming",
      label: "No Upcoming",
      description: "Events in Today and 6-day, but nothing in À venir",
    },
  ];

  const previewsHtml = debugModes
    .map(({ mode, label, description }) => {
      const url = mode
        ? `/calendar/preview?debug=${mode}`
        : "/calendar/preview";
      return `
      <div class="preview-card">
        <h3>${label}</h3>
        <p>${description}</p>
        <a href="${url}" target="_blank">
          <img src="${url}" alt="${label}" loading="lazy" />
        </a>
      </div>
    `;
    })
    .join("");

  res.send(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>EPCAL Debug Previews</title>
      <style>
        body {
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
          max-width: 1400px;
          margin: 0 auto;
          padding: 20px;
          background: #f5f5f5;
        }
        h1 { margin-bottom: 10px; }
        .back-link { margin-bottom: 20px; display: block; }
        .previews {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(600px, 1fr));
          gap: 20px;
        }
        .preview-card {
          background: white;
          border-radius: 8px;
          padding: 15px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .preview-card h3 { margin: 0 0 5px 0; }
        .preview-card p { margin: 0 0 10px 0; color: #666; font-size: 14px; }
        .preview-card img {
          width: 100%;
          height: auto;
          border: 1px solid #ddd;
          border-radius: 4px;
        }
        .preview-card a { text-decoration: none; }
      </style>
    </head>
    <body>
      <a href="/" class="back-link">← Back to Config</a>
      <h1>Debug Previews</h1>
      <p>Click any image to open full size in a new tab.</p>
      <div class="previews">
        ${previewsHtml}
      </div>
    </body>
    </html>
  `);
});

// Weather forecast data structure
interface WeatherForecast {
  datetime: string;
  condition: string;
  temperature: number | null; // High temp (can be null for current day)
  templow: number | null; // Low temp
  precipitation_probability: number;
}

// Fetch weather forecast using Home Assistant's weather.get_forecasts service (HA 2024.1+)
async function fetchWeatherForecast(
  entityId: string,
  type: "daily" | "hourly" = "daily",
): Promise<WeatherForecast[] | null> {
  if (!config) return null;

  try {
    // Use the weather.get_forecasts service with ?return_response query param
    const response = await fetch(
      `${config.haUrl}/api/services/weather/get_forecasts?return_response`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${config.haToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          type: type,
          entity_id: entityId,
        }),
      },
    );

    if (response.ok) {
      const result = (await response.json()) as {
        service_response?: Record<string, { forecast?: WeatherForecast[] }>;
      };
      // Response format: { "service_response": { "weather.entity_id": { "forecast": [...] } } }
      const forecast = result?.service_response?.[entityId]?.forecast;
      if (forecast) {
        return forecast;
      }
    }
  } catch (e) {
    console.error(`Failed to fetch forecast for ${entityId}:`, e);
  }

  return null;
}

// Get weather data for rendering (converts HA forecast to DayForecast format)
async function getWeatherForRendering(): Promise<DayForecast[]> {
  if (!config?.weatherEntity) {
    return [];
  }

  try {
    const forecasts = await fetchWeatherForecast(config.weatherEntity);
    if (!forecasts || forecasts.length === 0) {
      return [];
    }

    return forecasts.map((f) => ({
      date: startOfDay(parseISO(f.datetime)),
      condition: f.condition,
      tempHigh: f.temperature,
      tempLow: f.templow,
    }));
  } catch (e) {
    console.error("Failed to get weather for rendering:", e);
    return [];
  }
}

// Debug endpoint to explore weather entities
app.get("/debug/weather", async (req, res) => {
  try {
    // Get all states and filter for weather entities
    const states = await haFetch("/api/states");
    const weatherEntities = states.filter((s: any) =>
      s.entity_id.startsWith("weather."),
    );

    // For each weather entity, try to get forecast
    const results = await Promise.all(
      weatherEntities.map(async (entity: any) => {
        // Check if forecast is in attributes (older HA versions)
        let forecast = entity.attributes.forecast || null;

        // If not, try template API
        if (!forecast) {
          forecast = await fetchWeatherForecast(entity.entity_id);
        }

        return {
          entity_id: entity.entity_id,
          state: entity.state,
          attributes: {
            temperature: entity.attributes.temperature,
            temperature_unit: entity.attributes.temperature_unit,
            humidity: entity.attributes.humidity,
            wind_speed: entity.attributes.wind_speed,
            wind_speed_unit: entity.attributes.wind_speed_unit,
            friendly_name: entity.attributes.friendly_name,
            supported_features: entity.attributes.supported_features,
          },
          forecast: forecast,
        };
      }),
    );

    res.json(results);
  } catch (e) {
    res.status(500).json({ error: String(e) });
  }
});

// Debug endpoint to see raw events
app.get("/debug/events", async (req, res) => {
  try {
    const { events, calendarIds } = await fetchAllEvents();
    const dateFilter = req.query.date as string;
    let filtered = events;
    if (dateFilter) {
      filtered = events.filter(
        (e) =>
          e.start.toISOString().startsWith(dateFilter) ||
          e.end.toISOString().startsWith(dateFilter),
      );
    }
    res.json(
      filtered.map((e) => ({
        title: e.title,
        start: e.start.toISOString(),
        end: e.end.toISOString(),
        allDay: e.allDay,
        calendarIcon: e.calendarIcon,
      })),
    );
  } catch (e) {
    res.status(500).json({ error: String(e) });
  }
});

// Test endpoint to visualize icon alignment
app.get("/calendar/icon-test", async (_req, res) => {
  const { createCanvas } = await import("canvas");

  const canvas = createCanvas(900, 400);
  const ctx = canvas.getContext("2d");

  // White background
  ctx.fillStyle = "#FFFFFF";
  ctx.fillRect(0, 0, 900, 400);

  ctx.lineWidth = 1;

  // Test at 11px (week section font)
  const fontSize = 11;

  // Title
  ctx.font = "bold 12px sans-serif";
  ctx.textBaseline = "top";
  ctx.fillStyle = "#000000";
  ctx.fillText(
    "11px - Goal: icon bottom aligns with '09:00' bottom. Red line = text bottom.",
    10,
    8,
  );

  ctx.font = `${fontSize}px sans-serif`;
  ctx.textBaseline = "top";

  // Measure reference text "09:00"
  const timeMetrics = ctx.measureText("09:00");
  const timeHeight =
    timeMetrics.actualBoundingBoxAscent + timeMetrics.actualBoundingBoxDescent;

  CALENDAR_ICONS.forEach((icon, i) => {
    const x = 30 + (i % 8) * 105;
    const rowY = 40 + Math.floor(i / 8) * 160;

    // Draw time text for reference
    ctx.fillStyle = "#000000";
    ctx.fillText("09:00", x, rowY);

    // Draw baseline where time text bottom is
    const timeBottom = rowY + timeHeight;
    ctx.strokeStyle = "#FF0000";
    ctx.beginPath();
    ctx.moveTo(x, timeBottom);
    ctx.lineTo(x + 95, timeBottom);
    ctx.stroke();

    // Measure icon
    const iconMetrics = ctx.measureText(icon);
    const iconHeight =
      iconMetrics.actualBoundingBoxAscent +
      iconMetrics.actualBoundingBoxDescent;

    // Calculate offset to align icon bottom with time bottom
    const offsetForBottomAlign = timeHeight - iconHeight;

    // Draw icon WITHOUT offset (gray)
    ctx.fillStyle = "#AAAAAA";
    ctx.fillText(icon, x + 40, rowY);

    // Draw icon WITH bottom-align offset (black)
    ctx.fillStyle = "#000000";
    ctx.fillText(icon, x + 55, rowY + offsetForBottomAlign);

    // Show values
    ctx.font = "9px sans-serif";
    ctx.fillStyle = "#666666";
    ctx.fillText(`${icon} h=${iconHeight.toFixed(1)}`, x + 40, rowY + 20);
    ctx.fillText(`off=${offsetForBottomAlign.toFixed(1)}`, x + 40, rowY + 32);
    ctx.fillText(
      `factor=${(offsetForBottomAlign / fontSize).toFixed(2)}`,
      x + 40,
      rowY + 44,
    );

    ctx.font = `${fontSize}px sans-serif`;
  });

  const png = canvas.toBuffer("image/png");
  res.setHeader("Content-Type", "image/png");
  res.send(png);
});

// Check endpoint - returns 304 if unchanged, or just the ETag
app.get("/calendar/check", async (req, res) => {
  try {
    const render = await getOrRenderCalendar();
    const clientEtag = req.headers["if-none-match"];

    if (clientEtag === render.etag) {
      return res.status(304).end();
    }

    res.setHeader("ETag", render.etag);
    res.setHeader("X-Render-Time", render.timestamp.toISOString());
    res.json({ etag: render.etag, timestamp: render.timestamp });
  } catch (e) {
    console.error("Error in /calendar/check:", e);
    res.status(500).send("Error checking calendar");
  }
});

// Black layer, chunk 1 (top half)
app.get("/calendar/black1", async (req, res) => {
  try {
    const render = await getOrRenderCalendar();
    const clientEtag = req.headers["if-none-match"];

    if (clientEtag === render.etag) {
      return res.status(304).end();
    }

    const chunk = extractChunk(render.blackLayer, 1);
    res.setHeader("Content-Type", "application/octet-stream");
    res.setHeader("ETag", render.etag);
    res.setHeader("X-Render-Time", render.timestamp.toISOString());
    res.send(chunk);
  } catch (e) {
    console.error("Error in /calendar/black1:", e);
    res.status(500).send("Error fetching black1");
  }
});

// Black layer, chunk 2 (bottom half)
app.get("/calendar/black2", async (req, res) => {
  try {
    const render = await getOrRenderCalendar();
    const clientEtag = req.headers["if-none-match"];

    if (clientEtag === render.etag) {
      return res.status(304).end();
    }

    const chunk = extractChunk(render.blackLayer, 2);
    res.setHeader("Content-Type", "application/octet-stream");
    res.setHeader("ETag", render.etag);
    res.setHeader("X-Render-Time", render.timestamp.toISOString());
    res.send(chunk);
  } catch (e) {
    console.error("Error in /calendar/black2:", e);
    res.status(500).send("Error fetching black2");
  }
});

// Red layer, chunk 1 (top half)
app.get("/calendar/red1", async (req, res) => {
  try {
    const render = await getOrRenderCalendar();
    const clientEtag = req.headers["if-none-match"];

    if (clientEtag === render.etag) {
      return res.status(304).end();
    }

    const chunk = extractChunk(render.redLayer, 1);
    res.setHeader("Content-Type", "application/octet-stream");
    res.setHeader("ETag", render.etag);
    res.setHeader("X-Render-Time", render.timestamp.toISOString());
    res.send(chunk);
  } catch (e) {
    console.error("Error in /calendar/red1:", e);
    res.status(500).send("Error fetching red1");
  }
});

// Red layer, chunk 2 (bottom half)
app.get("/calendar/red2", async (req, res) => {
  try {
    const render = await getOrRenderCalendar();
    const clientEtag = req.headers["if-none-match"];

    if (clientEtag === render.etag) {
      return res.status(304).end();
    }

    const chunk = extractChunk(render.redLayer, 2);
    res.setHeader("Content-Type", "application/octet-stream");
    res.setHeader("ETag", render.etag);
    res.setHeader("X-Render-Time", render.timestamp.toISOString());
    res.send(chunk);
  } catch (e) {
    console.error("Error in /calendar/red2:", e);
    res.status(500).send("Error fetching red2");
  }
});
