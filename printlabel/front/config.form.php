<?php

// GLPI 11+ boots the app before running plugin scripts; GLPI 10 needs the include
if (!defined('GLPI_ROOT') || !class_exists('Session', false)) {
    include __DIR__ . '/../../../inc/includes.php';
}

Session::checkRight('config', UPDATE);

if (isset($_POST['update'])) {
    Config::setConfigurationValues('plugin:printlabel', [
        'agent_url' => rtrim(trim($_POST['agent_url'] ?? ''), '/'),
        'patterns'  => trim(str_replace("\r", '', $_POST['patterns'] ?? '')),
    ]);
    Session::addMessageAfterRedirect(__('Item successfully updated'));
    Html::back();
}

$config = plugin_printlabel_config();
$e = fn($v) => htmlspecialchars($v, ENT_QUOTES);

Html::header('Print label', '', 'config', 'plugin');

echo <<<HTML
<div class="container-lg">
  <form method="post" action="" class="card">
    <div class="card-header"><h3 class="card-title">Print label settings</h3></div>
    <div class="card-body">
      <div class="mb-3">
        <label class="form-label" for="printlabel_agent_url">Agent URL</label>
        <input class="form-control" id="printlabel_agent_url" name="agent_url" value="{$e($config['agent_url'])}">
        <div class="form-hint">
          Address of the glpi-label agent, as seen from the user's browser.
          Default: <code>http://127.0.0.1:9123</code> (agent running on the user's own computer).
        </div>
      </div>
      <div class="mb-3">
        <label class="form-label" for="printlabel_patterns">Label text patterns</label>
        <textarea class="form-control font-monospace" rows="7" id="printlabel_patterns" name="patterns">{$e($config['patterns'])}</textarea>
        <div class="form-hint">
          One <code>itemtype=pattern</code> per line (itemtype as in the URL: computer, monitor,
          printer, phone, networkequipment, peripheral...). <code>default</code> applies to the others.<br>
          Placeholders: <code>{name}</code> <code>{otherserial}</code> (inventory number)
          <code>{serial}</code> <code>{id}</code> <code>{itemtype}</code> <code>{type}</code>
          (the item's type dropdown). Use <code>{type|itemtype}</code> for a fallback and
          <code>{type:upper}</code> / <code>:lower</code> to change case.
          If a placeholder is empty, the item name is used.<br>
          Example: <code>default=ACME-{itemtype:upper}-{otherserial}</code>
        </div>
      </div>
    </div>
    <div class="card-footer text-end">
      <button type="submit" name="update" value="1" class="btn btn-primary">Save</button>
    </div>
HTML;
Html::closeForm();
echo '</div>';

Html::footer();
