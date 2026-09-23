import { describe, it, expect } from 'vitest';
import {
  normalizeTemperature,
  getThermalColor,
  getThermalEmissive,
  getThermalStatus,
  DEFAULT_THERMAL_CONFIG,
} from '../thermal';

describe('Thermal Color Mapping Logic', () => {
  const config = DEFAULT_THERMAL_CONFIG; // minTemp: 30, maxTemp: 150

  it('normalizes minimum configured temperature to 0.0', () => {
    expect(normalizeTemperature(config.minTempC, config)).toBe(0.0);
  });

  it('normalizes maximum configured temperature to 1.0', () => {
    expect(normalizeTemperature(config.maxTempC, config)).toBe(1.0);
  });

  it('normalizes mid-range temperature to 0.5', () => {
    const midTemp = (config.minTempC + config.maxTempC) / 2.0; // (30 + 150) / 2 = 90
    expect(normalizeTemperature(midTemp, config)).toBeCloseTo(0.5, 6);
  });

  it('clamps out-of-bounds low and high temperatures', () => {
    expect(normalizeTemperature(-20.0, config)).toBe(0.0);
    expect(normalizeTemperature(250.0, config)).toBe(1.0);
    expect(normalizeTemperature(NaN, config)).toBe(0.0);
  });

  it('generates cold sky blue color at minimum temperature', () => {
    const coldColor = getThermalColor(config.minTempC, config);
    // Cold color stop is #0ea5e9 -> high blue, low red
    expect(coldColor.b).toBeGreaterThan(coldColor.r);
  });

  it('generates hot red color at peak temperature', () => {
    const hotColor = getThermalColor(config.maxTempC, config);
    // Peak color stop is #ef4444 -> high red, low blue
    expect(hotColor.r).toBeGreaterThan(hotColor.b);
  });

  it('increases emissive intensity only above 50% thermal load', () => {
    const coldEmissive = getThermalEmissive(40.0, config);
    const hotEmissive = getThermalEmissive(140.0, config);

    expect(coldEmissive.intensity).toBeCloseTo(0.05, 2);
    expect(hotEmissive.intensity).toBeGreaterThan(0.4);
    expect(hotEmissive.color.r).toBeGreaterThan(hotEmissive.color.b);
  });

  it('correctly maps CHT to thermal status categories', () => {
    expect(getThermalStatus(35.0).status).toBe('COLD');
    expect(getThermalStatus(95.0).status).toBe('OPTIMAL');
    expect(getThermalStatus(125.0).status).toBe('ELEVATED');
    expect(getThermalStatus(155.0).status).toBe('OVERHEAT');
  });
});
