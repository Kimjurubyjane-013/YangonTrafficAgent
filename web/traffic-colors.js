(function () {
    'use strict';
    const palette = Object.freeze({
        Light: Object.freeze({ css: '#2F9E68', three: 0x2F9E68 }),
        Moderate: Object.freeze({ css: '#D88918', three: 0xD88918 }),
        Heavy: Object.freeze({ css: '#D94B42', three: 0xD94B42 }),
        Unknown: Object.freeze({ css: '#71808A', three: 0x71808A }),
    });
    const normalize = value => {
        const match = Object.keys(palette).find(key => key.toLowerCase() === String(value || '').trim().toLowerCase());
        return match || null;
    };
    const css = value => palette[normalize(value) || 'Unknown'].css;
    const three = value => palette[normalize(value) || 'Unknown'].three;
    const root = document.documentElement;
    Object.entries(palette).forEach(([level, color]) => {
        root.style.setProperty(`--traffic-${level.toLowerCase()}`, color.css);
    });
    window.YangonTrafficColors = Object.freeze({ palette, normalize, css, three, getTrafficColor: css });
}());
