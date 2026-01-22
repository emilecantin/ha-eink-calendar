import { describe, it, expect } from "@jest/globals";

/**
 * Tests for async/await patterns that should be caught by ESLint
 * These tests demonstrate the types of bugs we want to prevent
 */

describe("async/await patterns", () => {
  describe("Promise handling", () => {
    it("should properly await async functions", async () => {
      const asyncFunction = async () => {
        return new Promise((resolve) => setTimeout(() => resolve("done"), 10));
      };

      // Correct: await the promise
      const result = await asyncFunction();
      expect(result).toBe("done");
    });

    it("should catch missing await (would be caught by ESLint)", async () => {
      const asyncFunction = async () => {
        return "immediate";
      };

      // This test shows that without await, you get a Promise
      const resultWithoutAwait = asyncFunction(); // Missing await
      expect(resultWithoutAwait).toBeInstanceOf(Promise);

      // Correct: with await
      const resultWithAwait = await asyncFunction();
      expect(resultWithAwait).toBe("immediate");
    });

    it("should properly return await from async functions", async () => {
      const fetchData = async () => {
        return await Promise.resolve({ data: "test" });
      };

      const result = await fetchData();
      expect(result).toEqual({ data: "test" });
    });
  });

  describe("Promise.all for parallel operations", () => {
    it("should use Promise.all for parallel async operations", async () => {
      const operation1 = async () => {
        await new Promise((resolve) => setTimeout(resolve, 20));
        return "op1";
      };

      const operation2 = async () => {
        await new Promise((resolve) => setTimeout(resolve, 20));
        return "op2";
      };

      // Correct: parallel execution
      const startTime = Date.now();
      const [result1, result2] = await Promise.all([
        operation1(),
        operation2(),
      ]);
      const duration = Date.now() - startTime;

      expect(result1).toBe("op1");
      expect(result2).toBe("op2");
      // Should complete in ~20ms (parallel), not ~40ms (sequential)
      // Use more forgiving threshold to avoid flakiness
      expect(duration).toBeLessThan(35);
    });

    it("should demonstrate sequential vs parallel execution", async () => {
      const delay = (ms: number) =>
        new Promise((resolve) => setTimeout(resolve, ms));

      // Sequential (slower)
      const sequentialStart = Date.now();
      await delay(10);
      await delay(10);
      const sequentialDuration = Date.now() - sequentialStart;

      // Parallel (faster)
      const parallelStart = Date.now();
      await Promise.all([delay(10), delay(10)]);
      const parallelDuration = Date.now() - parallelStart;

      expect(sequentialDuration).toBeGreaterThanOrEqual(20);
      expect(parallelDuration).toBeLessThan(sequentialDuration);
    });
  });

  describe("Error handling in async functions", () => {
    it("should properly catch errors in async functions", async () => {
      const failingFunction = async () => {
        throw new Error("Test error");
      };

      await expect(failingFunction()).rejects.toThrow("Test error");
    });

    it("should handle rejected promises with try/catch", async () => {
      const riskyFunction = async () => {
        try {
          await Promise.reject(new Error("Failed"));
          return "success";
        } catch (error) {
          return "handled error";
        }
      };

      const result = await riskyFunction();
      expect(result).toBe("handled error");
    });
  });

  describe("Collection icons bug scenario", () => {
    /**
     * This simulates the bug we had where collection icons weren't being awaited
     */
    it("should demonstrate the importance of awaiting icon loading", async () => {
      const loadIcon = async (iconName: string): Promise<string> => {
        // Simulate async icon loading
        await new Promise((resolve) => setTimeout(resolve, 10));
        return `icon_${iconName}`;
      };

      const renderWithIcons = async (icons: string[]): Promise<string[]> => {
        // WRONG: Not awaiting the icon loading
        // const loadedIcons = icons.map(name => loadIcon(name));
        // return loadedIcons; // Returns array of Promises, not strings!

        // CORRECT: Use Promise.all to await all icon loads
        const loadedIcons = await Promise.all(
          icons.map((name) => loadIcon(name)),
        );
        return loadedIcons;
      };

      const result = await renderWithIcons(["trash", "recycling", "compost"]);
      expect(result).toEqual(["icon_trash", "icon_recycling", "icon_compost"]);
      // All results should be strings, not Promises
      expect(result.every((r) => typeof r === "string")).toBe(true);
    });

    it("should show what happens without proper await (the bug)", async () => {
      const loadIcon = async (iconName: string): Promise<string> => {
        await new Promise((resolve) => setTimeout(resolve, 10));
        return `icon_${iconName}`;
      };

      // Simulating the buggy version (without await)
      const renderWithIconsBuggy = (icons: string[]) => {
        // Missing 'async' and 'await'
        const loadedIcons = icons.map((name) => loadIcon(name));
        return loadedIcons; // Returns Promises!
      };

      const result = renderWithIconsBuggy(["trash", "recycling"]);
      // These are Promises, not strings - this was the bug!
      expect(result[0]).toBeInstanceOf(Promise);
      expect(result[1]).toBeInstanceOf(Promise);
    });
  });

  describe("Async function without await", () => {
    it("should not mark function as async if it does not await", () => {
      // This would be caught by ESLint require-await rule
      const unnecessarilyAsync = async () => {
        return "synchronous value";
      };

      // Even though it's marked async, it doesn't actually need to be
      const result = unnecessarilyAsync();
      expect(result).toBeInstanceOf(Promise);
    });

    it("should use async only when actually awaiting", async () => {
      // Correct: actually needs to be async
      const properlyAsync = async () => {
        const value = await Promise.resolve("async value");
        return value;
      };

      const result = await properlyAsync();
      expect(result).toBe("async value");
    });
  });
});
