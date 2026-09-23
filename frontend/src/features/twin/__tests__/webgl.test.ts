import { describe, it, expect } from 'vitest';
import { detectWebGLSupport } from '../webgl';

describe('WebGL Feature Detection', () => {
  it('runs detection without throwing errors', () => {
    expect(() => detectWebGLSupport()).not.toThrow();
  });

  it('returns a structured WebGLSupportResult', () => {
    const result = detectWebGLSupport();
    expect(result).toHaveProperty('supported');
    expect(result).toHaveProperty('version');
    expect(result).toHaveProperty('renderer');
    expect(result).toHaveProperty('vendor');
    expect(typeof result.supported).toBe('boolean');
    expect(['webgl2', 'webgl', 'none']).toContain(result.version);
  });
});
