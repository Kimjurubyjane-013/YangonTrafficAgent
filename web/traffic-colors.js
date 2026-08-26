(function () {
    'use strict';
    const palette = Object.freeze({
        Light: Object.freeze({ css: '#2F9E68', three: 0x2F9E68 }),
        Moderate: Object.freeze({ css: '#D88918', three: 0xD88918 }),
        Heavy: Object.freeze({ css: '#D94B42', three: 0xD94B42 }),
    });
    const normalize = value => Object.prototype.hasOwnProperty.call(palette, value) ? value : null;
    const css = (value, fallback = '#60717D') => palette[normalize(value)]?.css || fallback;
    const three = (value, fallback = 0x60717D) => palette[normalize(value)]?.three || fallback;
    const root = document.documentElement;
    Object.entries(palette).forEach(([level, color]) => {
        root.style.setProperty(`--traffic-${level.toLowerCase()}`, color.css);
    });
    window.YangonTrafficColors = Object.freeze({ palette, normalize, css, three });
}());
