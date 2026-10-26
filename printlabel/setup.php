<?php

/**
 * Print label for GLPI
 *
 * Adds a "Print label" button to asset forms. The button builds the label
 * text from a configurable pattern and sends it, with the item URL for the
 * QR code, to the glpi-label agent running on the user's own computer.
 *
 * @license GPL-3.0-or-later
 */

define('PLUGIN_PRINTLABEL_VERSION', '2.0.0');
define('PLUGIN_PRINTLABEL_MIN_GLPI', '10.0.0');
define('PLUGIN_PRINTLABEL_MAX_GLPI', '12.99.99');

const PLUGIN_PRINTLABEL_DEFAULTS = [
    // where the glpi-label agent listens, as seen from the user's browser
    'agent_url' => 'http://127.0.0.1:9123',
    // one "itemtype=pattern" per line, "default" applies to the others
    'patterns'  => 'default={name}',
];

function plugin_printlabel_config(): array
{
    $values = Config::getConfigurationValues('plugin:printlabel', array_keys(PLUGIN_PRINTLABEL_DEFAULTS));
    $values = array_filter($values, fn($v) => $v !== null && $v !== '');
    return array_merge(PLUGIN_PRINTLABEL_DEFAULTS, $values);
}

function plugin_init_printlabel()
{
    global $PLUGIN_HOOKS;

    $PLUGIN_HOOKS['csrf_compliant']['printlabel'] = true;

    if (!Plugin::isPluginActive('printlabel')) {
        return;
    }

    $PLUGIN_HOOKS['config_page']['printlabel'] = 'front/config.form.php';

    // GLPI 11+ serves plugin assets from public/, GLPI 10 from the plugin root
    $PLUGIN_HOOKS['add_javascript']['printlabel'] = version_compare(GLPI_VERSION, '11.0.0', '>=')
        ? 'js/printlabel.js'
        : 'public/js/printlabel.js';

    if (Session::getLoginUserID()) {
        // settings for the button script, read from <meta name="printlabel-config">
        $PLUGIN_HOOKS['add_header_tag']['printlabel'] = [[
            'tag'        => 'meta',
            'properties' => [
                'name'    => 'printlabel-config',
                'content' => json_encode(plugin_printlabel_config()),
            ],
        ]];
    }
}

function plugin_version_printlabel()
{
    return [
        'name'         => 'Print label',
        'version'      => PLUGIN_PRINTLABEL_VERSION,
        'author'       => 'Hedi Trigui',
        'license'      => 'GPLv3+',
        'homepage'     => 'https://github.com/heditrigui/glpi-printlabel',
        'requirements' => [
            'glpi' => [
                'min' => PLUGIN_PRINTLABEL_MIN_GLPI,
                'max' => PLUGIN_PRINTLABEL_MAX_GLPI,
            ],
        ],
    ];
}

function plugin_printlabel_check_prerequisites()
{
    return true;
}

function plugin_printlabel_check_config($verbose = false)
{
    return true;
}
