/**
 * WebGL feature detection and browser capability verification.
 */

export interface WebGLSupportResult {
  supported: boolean;
  version: 'webgl2' | 'webgl' | 'none';
  renderer: string;
  vendor: string;
  errorMessage?: string;
}

/**
 * Check if the host browser supports WebGL rendering.
 */
export function detectWebGLSupport(): WebGLSupportResult {
  try {
    const canvas = document.createElement('canvas');

    // Try WebGL 2 first
    let gl: WebGLRenderingContext | WebGL2RenderingContext | null =
      canvas.getContext('webgl2');
    let version: 'webgl2' | 'webgl' | 'none' = 'webgl2';

    if (!gl) {
      gl = canvas.getContext('webgl') || (canvas.getContext('experimental-webgl') as WebGLRenderingContext | null);
      version = 'webgl';
    }

    if (!gl) {
      return {
        supported: false,
        version: 'none',
        renderer: 'Unknown',
        vendor: 'Unknown',
        errorMessage: 'WebGL is not supported or is disabled in your browser environment.',
      };
    }

    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
    const renderer = debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : 'Generic WebGL';
    const vendor = debugInfo ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) : 'Generic Vendor';

    return {
      supported: true,
      version,
      renderer: String(renderer),
      vendor: String(vendor),
    };
  } catch (err) {
    return {
      supported: false,
      version: 'none',
      renderer: 'Unknown',
      vendor: 'Unknown',
      errorMessage: err instanceof Error ? err.message : 'Unknown WebGL initialization failure',
    };
  }
}
