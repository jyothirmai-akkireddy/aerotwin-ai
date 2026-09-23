import { describe, it, expect } from 'vitest';
import { useAppStore } from './useAppStore';

describe('useAppStore State Management', () => {
  it('has initial default state', () => {
    const state = useAppStore.getState();
    expect(state.activeTab).toBe('overview');
    expect(state.connectionStatus).toBe('CHECKING');
    expect(state.health).toBeNull();
    expect(state.readiness).toBeNull();
  });

  it('updates activeTab correctly', () => {
    useAppStore.getState().setActiveTab('twin');
    expect(useAppStore.getState().activeTab).toBe('twin');

    useAppStore.getState().setActiveTab('diagnostics');
    expect(useAppStore.getState().activeTab).toBe('diagnostics');

    useAppStore.getState().setActiveTab('overview');
    expect(useAppStore.getState().activeTab).toBe('overview');
  });

  it('clears error message', () => {
    useAppStore.setState({ errorMessage: 'Test error message' });
    expect(useAppStore.getState().errorMessage).toBe('Test error message');

    useAppStore.getState().clearError();
    expect(useAppStore.getState().errorMessage).toBeNull();
  });
});
