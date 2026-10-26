<?php

function plugin_printlabel_install()
{
    $current = Config::getConfigurationValues('plugin:printlabel', array_keys(PLUGIN_PRINTLABEL_DEFAULTS));
    Config::setConfigurationValues('plugin:printlabel', array_merge(PLUGIN_PRINTLABEL_DEFAULTS, array_filter($current)));
    return true;
}

function plugin_printlabel_uninstall()
{
    Config::deleteConfigurationValues('plugin:printlabel', array_keys(PLUGIN_PRINTLABEL_DEFAULTS));
    return true;
}
