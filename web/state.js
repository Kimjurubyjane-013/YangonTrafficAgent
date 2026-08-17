(function () {
    'use strict';
    const phases = Object.freeze({ IDLE:'idle', LOADING:'loading', READY:'route-ready', SIMULATING:'simulating', PAUSED:'paused', ARRIVED:'arrived', ERROR:'error' });
    let value = Object.freeze({ phase: phases.IDLE, requestId: 0 });
    const listeners = new Set();
    window.YangonAppState = {
        phases,
        get: () => value,
        set(patch) { value = Object.freeze({ ...value, ...patch }); listeners.forEach(listener => listener(value)); return value; },
        nextRequest() { return this.set({ requestId: value.requestId + 1, phase: phases.LOADING }).requestId; },
        subscribe(listener) { listeners.add(listener); listener(value); return () => listeners.delete(listener); }
    };
}());
