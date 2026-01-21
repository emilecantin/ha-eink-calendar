import { describe, it, expect } from '@jest/globals';

/**
 * Tests for collection icon matching logic
 * This feature had async/await bugs, so these tests ensure correct behavior
 */

describe('Collection icon matching', () => {
  describe('Title-based type matching', () => {
    const collectionTypes = [
      { name: 'Garbage', icon: '🗑️' },
      { name: 'Recycling', icon: '♻️' },
      { name: 'Compost', icon: '🍂' },
    ];

    const matchCollectionType = (
      title: string,
      types: typeof collectionTypes,
    ): string | null => {
      const titleLower = title.toLowerCase();
      for (const type of types) {
        if (titleLower.includes(type.name.toLowerCase())) {
          return type.icon;
        }
      }
      return null;
    };

    it('should match exact title', () => {
      expect(matchCollectionType('Garbage', collectionTypes)).toBe('🗑️');
      expect(matchCollectionType('Recycling', collectionTypes)).toBe('♻️');
      expect(matchCollectionType('Compost', collectionTypes)).toBe('🍂');
    });

    it('should match case-insensitively', () => {
      expect(matchCollectionType('GARBAGE', collectionTypes)).toBe('🗑️');
      expect(matchCollectionType('garbage', collectionTypes)).toBe('🗑️');
      expect(matchCollectionType('GaRbAgE', collectionTypes)).toBe('🗑️');
    });

    it('should match title containing type name', () => {
      expect(matchCollectionType('Garbage Collection Day', collectionTypes)).toBe(
        '🗑️',
      );
      expect(matchCollectionType('Weekly Recycling Pickup', collectionTypes)).toBe(
        '♻️',
      );
      expect(matchCollectionType('Compost Bin Day', collectionTypes)).toBe('🍂');
    });

    it('should return null for non-matching titles', () => {
      expect(matchCollectionType('Random Event', collectionTypes)).toBeNull();
      expect(matchCollectionType('Meeting', collectionTypes)).toBeNull();
      expect(matchCollectionType('', collectionTypes)).toBeNull();
    });

    it('should match first type when multiple match', () => {
      // If title contains multiple keywords, return first match
      const result = matchCollectionType(
        'Garbage and Recycling Day',
        collectionTypes,
      );
      expect(result).toBe('🗑️'); // Garbage comes first in types array
    });
  });

  describe('Calendar-based filtering', () => {
    interface Event {
      id: string;
      title: string;
      calendarId: string;
      allDay: boolean;
    }

    const events: Event[] = [
      {
        id: '1',
        title: 'Garbage Day',
        calendarId: 'calendar.collection',
        allDay: true,
      },
      {
        id: '2',
        title: 'Team Meeting',
        calendarId: 'calendar.work',
        allDay: false,
      },
      {
        id: '3',
        title: 'Recycling',
        calendarId: 'calendar.collection',
        allDay: true,
      },
    ];

    it('should filter events from collection calendars', () => {
      const collectionCalendars = ['calendar.collection'];
      const filtered = events.filter((e) =>
        collectionCalendars.includes(e.calendarId),
      );

      expect(filtered).toHaveLength(2);
      expect(filtered[0].title).toBe('Garbage Day');
      expect(filtered[1].title).toBe('Recycling');
    });

    it('should only include all-day events from collection calendars', () => {
      const collectionCalendars = ['calendar.collection'];
      const filtered = events.filter(
        (e) => collectionCalendars.includes(e.calendarId) && e.allDay,
      );

      expect(filtered).toHaveLength(2);
      expect(filtered.every((e) => e.allDay)).toBe(true);
    });

    it('should handle empty collection calendars list', () => {
      const collectionCalendars: string[] = [];
      const filtered = events.filter((e) =>
        collectionCalendars.includes(e.calendarId),
      );

      expect(filtered).toHaveLength(0);
    });

    it('should handle multiple collection calendars', () => {
      const allEvents: Event[] = [
        ...events,
        {
          id: '4',
          title: 'Yard Waste',
          calendarId: 'calendar.municipal',
          allDay: true,
        },
      ];

      const collectionCalendars = ['calendar.collection', 'calendar.municipal'];
      const filtered = allEvents.filter((e) =>
        collectionCalendars.includes(e.calendarId),
      );

      expect(filtered).toHaveLength(3);
    });
  });

  describe('Async icon loading (the bug scenario)', () => {
    /**
     * This simulates the actual bug we had where collection icons
     * weren't being awaited properly with Promise.all
     */

    const loadCollectionIcon = async (eventTitle: string): Promise<string> => {
      // Simulate async icon loading/matching
      await new Promise((resolve) => setTimeout(resolve, 1));

      const types = [
        { name: 'Garbage', icon: '🗑️' },
        { name: 'Recycling', icon: '♻️' },
      ];

      const titleLower = eventTitle.toLowerCase();
      for (const type of types) {
        if (titleLower.includes(type.name.toLowerCase())) {
          return type.icon;
        }
      }
      return '';
    };

    it('should correctly await all icon loads with Promise.all', async () => {
      const events = ['Garbage Day', 'Recycling Day', 'Compost Day'];

      // CORRECT: Use Promise.all to await all icon loads
      const icons = await Promise.all(
        events.map((title) => loadCollectionIcon(title)),
      );

      expect(icons).toEqual(['🗑️', '♻️', '']);
      expect(icons.every((icon) => typeof icon === 'string')).toBe(true);
    });

    it('should demonstrate the bug when not using await', async () => {
      const events = ['Garbage Day', 'Recycling Day'];

      // WRONG: Missing await on the map result
      const iconsPromises = events.map((title) => loadCollectionIcon(title));

      // These are Promises, not strings! (This was the bug)
      expect(iconsPromises[0]).toBeInstanceOf(Promise);
      expect(iconsPromises[1]).toBeInstanceOf(Promise);

      // To fix, we need to await them
      const icons = await Promise.all(iconsPromises);
      expect(icons).toEqual(['🗑️', '♻️']);
    });

    it('should handle events with no matching icons', async () => {
      const events = ['Meeting', 'Lunch', 'Garbage Day'];

      const icons = await Promise.all(
        events.map((title) => loadCollectionIcon(title)),
      );

      expect(icons).toEqual(['', '', '🗑️']);
    });
  });

  describe('Integration: Full collection icon workflow', () => {
    interface CalendarEvent {
      id: string;
      title: string;
      calendarId: string;
      allDay: boolean;
      start: Date;
    }

    const processCollectionEvents = async (
      events: CalendarEvent[],
      collectionCalendars: string[],
      collectionTypes: Array<{ name: string; icon: string }>,
    ): Promise<Array<{ date: string; icon: string; title: string }>> => {
      // Filter to collection calendars and all-day events
      const collectionEvents = events.filter(
        (e) => collectionCalendars.includes(e.calendarId) && e.allDay,
      );

      // Match icons for each event (MUST use Promise.all!)
      const eventsWithIcons = await Promise.all(
        collectionEvents.map(async (event) => {
          const titleLower = event.title.toLowerCase();
          let icon = '';

          for (const type of collectionTypes) {
            if (titleLower.includes(type.name.toLowerCase())) {
              icon = type.icon;
              break;
            }
          }

          return {
            date: event.start.toDateString(),
            icon,
            title: event.title,
          };
        }),
      );

      // Filter out events with no matching icon
      return eventsWithIcons.filter((e) => e.icon !== '');
    };

    it('should process collection events with correct icons', async () => {
      const events: CalendarEvent[] = [
        {
          id: '1',
          title: 'Garbage Collection',
          calendarId: 'calendar.waste',
          allDay: true,
          start: new Date('2024-01-15'),
        },
        {
          id: '2',
          title: 'Recycling Pickup',
          calendarId: 'calendar.waste',
          allDay: true,
          start: new Date('2024-01-16'),
        },
        {
          id: '3',
          title: 'Team Meeting',
          calendarId: 'calendar.work',
          allDay: false,
          start: new Date('2024-01-15'),
        },
      ];

      const collectionTypes = [
        { name: 'Garbage', icon: '🗑️' },
        { name: 'Recycling', icon: '♻️' },
      ];

      const result = await processCollectionEvents(
        events,
        ['calendar.waste'],
        collectionTypes,
      );

      expect(result).toHaveLength(2);
      expect(result[0].icon).toBe('🗑️');
      expect(result[0].title).toBe('Garbage Collection');
      expect(result[1].icon).toBe('♻️');
      expect(result[1].title).toBe('Recycling Pickup');
    });

    it('should exclude events with no matching icon', async () => {
      const events: CalendarEvent[] = [
        {
          id: '1',
          title: 'Unknown Collection Type',
          calendarId: 'calendar.waste',
          allDay: true,
          start: new Date('2024-01-15'),
        },
      ];

      const collectionTypes = [{ name: 'Garbage', icon: '🗑️' }];

      const result = await processCollectionEvents(
        events,
        ['calendar.waste'],
        collectionTypes,
      );

      expect(result).toHaveLength(0);
    });
  });
});
