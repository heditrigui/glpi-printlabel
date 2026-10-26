/**
 * Print label for GLPI: adds a "Print label" button to asset forms and sends
 * the label text + item URL to the glpi-label agent.
 *
 * @license GPL-3.0-or-later
 */
(function () {
    'use strict';

    const match = window.location.pathname.match(/\/front\/(\w+)\.form\.php$/);
    const id = parseInt(new URLSearchParams(window.location.search).get('id') || '0', 10);
    if (!match || id <= 0) {
        return;
    }
    const itemtype = match[1].toLowerCase();

    const readConfig = () => {
        const meta = document.querySelector('meta[name="printlabel-config"]');
        let cfg = {};
        try {
            cfg = meta ? JSON.parse(meta.content) : {};
        } catch (e) {
            // keep defaults
        }
        const patterns = {};
        (cfg.patterns || 'default={name}').split('\n').forEach((line) => {
            const i = line.indexOf('=');
            if (i > 0) {
                patterns[line.slice(0, i).trim().toLowerCase()] = line.slice(i + 1).trim();
            }
        });
        return {
            agentUrl: (cfg.agent_url || 'http://127.0.0.1:9123').replace(/\/+$/, ''),
            pattern: patterns[itemtype] || patterns.default || '{name}',
        };
    };

    const field = (name) => {
        const el = document.querySelector(`form [name="${name}"]`);
        if (!el) {
            return '';
        }
        if (el.tagName === 'SELECT') {
            const opt = el.options[el.selectedIndex];
            return opt && el.value !== '0' && el.value !== '' ? opt.text.trim() : '';
        }
        return (el.value || '').trim();
    };

    const values = () => ({
        name: field('name'),
        otherserial: field('otherserial'),
        serial: field('serial'),
        id: String(id),
        itemtype: itemtype,
        type: field(`${itemtype}types_id`),
    });

    // "{a|b:upper}" -> first non-empty of a, b, upper-cased
    const render = (pattern, vals) => {
        let missing = false;
        const text = pattern.replace(/\{([^}]+)\}/g, (_, expr) => {
            const [names, modifier] = expr.split(':');
            let v = '';
            for (const n of names.split('|')) {
                v = vals[n.trim()] || '';
                if (v) {
                    break;
                }
            }
            if (!v) {
                missing = true;
            }
            if (modifier === 'upper') {
                v = v.toUpperCase();
            } else if (modifier === 'lower') {
                v = v.toLowerCase();
            }
            return v;
        });
        return missing ? vals.name : text;
    };

    const notify = (msg, ok) => {
        const fn = ok ? window.glpi_toast_info : window.glpi_toast_error;
        typeof fn === 'function' ? fn(msg) : alert(msg);
    };

    const print = async () => {
        const cfg = readConfig();
        const name = prompt('Label text', render(cfg.pattern, values()));
        if (!name) {
            return;
        }
        const url = `${window.location.origin}${window.location.pathname}?id=${id}`;
        try {
            const r = await fetch(`${cfg.agentUrl}/print`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name: name, url: url}),
            });
            const res = await r.json();
            if (!r.ok) {
                throw new Error(res.error || r.status);
            }
            notify('Label printed: ' + name, true);
        } catch (e) {
            notify(`Label not printed (is the glpi-label agent running at ${cfg.agentUrl}?): ${e.message}`, false);
        }
    };

    // only asset forms: they have an inventory number field and a Save button
    const addButton = () => {
        if (document.getElementById('printlabel-btn')) {
            return true;
        }
        const save = document.querySelector('form button[name="update"]');
        if (!save || !document.querySelector('form [name="otherserial"]')) {
            return false;
        }
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.id = 'printlabel-btn';
        btn.className = 'btn btn-outline-secondary me-2';
        btn.innerHTML = '<i class="ti ti-qrcode me-1"></i>Print label';
        btn.addEventListener('click', print);
        save.parentNode.insertBefore(btn, save);
        return true;
    };

    // the main form can be loaded after the page (tabs are fetched by AJAX)
    const start = () => {
        if (addButton()) {
            return;
        }
        const obs = new MutationObserver(() => {
            if (addButton()) {
                obs.disconnect();
            }
        });
        obs.observe(document.body, {childList: true, subtree: true});
    };
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', start);
    } else {
        start();
    }
})();
