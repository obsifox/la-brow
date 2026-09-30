const state = {
  profiles: [],
  resolvers: [],
  settings: {},
  selectedProfile: "default",
  snapshot: null
};

const endpoints = [
  ["GET", "/api/health", "service state and capabilities"],
  ["GET", "/api/environment", "resolve the environment pipeline for an address"],
  ["GET", "/api/consistency", "consistency findings across surfaces"],
  ["GET", "/api/profiles", "list built-in and stored profiles"],
  ["POST", "/api/profiles", "create or replace a profile"],
  ["GET", "/api/profiles/{id}", "read one profile"],
  ["PUT", "/api/profiles/{id}", "update one profile"],
  ["DELETE", "/api/profiles/{id}", "delete one profile"],
  ["POST", "/api/profiles/validate", "validate without storing"],
  ["POST", "/api/profiles/import", "validate, migrate and optionally activate an imported payload"],
  ["GET", "/api/profiles/{id}/export", "export a signed envelope"],
  ["POST", "/api/profiles/{id}/rollback", "restore the previous revision"],
  ["GET", "/api/resolvers", "list resolver profiles"],
  ["POST", "/api/dns/probe", "resolve a name through a selected resolver"],
  ["GET", "/api/dns/diagnostics", "resolver diagnostics and isolation state"],
  ["GET", "/api/diagnostics", "diagnostic export at a redaction level"],
  ["GET", "/api/webrtc", "WebRTC policy presets with limits"],
  ["GET", "/api/identity", "identity assets and legibility report"],
  ["GET", "/api/scans", "policy scanner state"],
  ["GET", "/api/settings", "read settings"],
  ["PUT", "/api/settings", "write settings"],
  ["GET", "/api/requests", "recent request log"],
  ["GET", "/api/events", "structured events from the last resolution"],
  ["GET", "/api/extensions", "recorded desktop add-ons and themes"],
  ["POST", "/api/extensions/inspect", "compatibility report for a desktop manifest"],
  ["POST", "/api/extensions/install", "record an add-on after the notice is acknowledged"],
  ["DELETE", "/api/extensions/{id}", "remove an add-on or theme"],
  ["GET", "/api/themes", "recorded themes and the active gradient"],
  ["PUT", "/api/themes/active", "activate a recorded theme"],
  ["GET", "/api/compat/firefox-desktop", "desktop compatibility matrix"]
];

function escapeHtml(value) {
  return String(value === null || value === undefined ? "not available" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function element(id) {
  return document.getElementById(id);
}

function setStatus(text, kind) {
  const node = element("status-line");
  node.textContent = text;
  node.className = "status" + (kind ? " " + kind : "");
}

function badgeClass(status) {
  if (status === "OK" || status === "PASS" || status === "VALID" || status === "CONSISTENT" || status === "SUCCESS") { return "ok"; }
  if (status === "FAIL" || status === "FAILED" || status === "INVALID" || status === "FAILURE") { return "fail"; }
  return "warn";
}

function badge(label, value, status) {
  return '<span class="badge ' + badgeClass(status) + '">' + escapeHtml(label) + ' <strong>' + escapeHtml(value) + '</strong></span>';
}

function kv(pairs) {
  return pairs.map(function (pair) {
    return '<div class="k">' + escapeHtml(pair[0]) + '</div><div class="v">' + escapeHtml(pair[1]) + '</div>';
  }).join("");
}

function table(headers, rows) {
  const head = headers.map(function (header) { return "<th>" + escapeHtml(header) + "</th>"; }).join("");
  const body = rows.map(function (row) {
    return "<tr>" + row.map(function (cell) { return "<td>" + escapeHtml(cell) + "</td>"; }).join("") + "</tr>";
  }).join("");
  return '<table><thead><tr>' + head + '</tr></thead><tbody>' + body + '</tbody></table>';
}

async function api(path, options) {
  const settings = options || {};
  const response = await fetch(path, {
    method: settings.method || "GET",
    headers: { "Content-Type": "application/json" },
    body: settings.body ? JSON.stringify(settings.body) : undefined
  });
  const payload = await response.json();
  if (!response.ok) {
    const message = payload && payload.error ? payload.error.message : "request failed with status " + response.status;
    const failure = new Error(message);
    failure.payload = payload;
    throw failure;
  }
  return payload;
}

function numberOrNull(value) {
  if (value === undefined || value === null || String(value).trim() === "") { return null; }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

async function loadHealth() {
  try {
    const payload = await api("/api/health");
    element("health-line").textContent = "version " + payload.version + " | profile schema " + payload.profile_version + " | " + payload.capabilities.length + " capabilities";
    setStatus("connected", "ok");
  } catch (error) {
    element("health-line").textContent = "application server unreachable";
    setStatus("offline", "fail");
  }
}

async function loadProfiles() {
  const payload = await api("/api/profiles");
  state.profiles = payload.profiles;
  const options = state.profiles.map(function (profile) {
    return '<option value="' + escapeHtml(profile.id) + '">' + escapeHtml(profile.id + " (" + profile.source + ")") + '</option>';
  }).join("");
  element("profile-select").innerHTML = options;
  element("env-profile").innerHTML = options;
  const active = state.settings.active_profile || "default";
  element("env-profile").value = active;
  element("profile-select").value = active;
}

async function loadResolvers() {
  const payload = await api("/api/resolvers");
  state.resolvers = payload.resolvers;
  const options = state.resolvers.map(function (profile) {
    return '<option value="' + escapeHtml(profile.id) + '">' + escapeHtml(profile.id + " | " + profile.protocol) + '</option>';
  }).join("");
  element("env-resolver").innerHTML = options;
  element("dns-resolver").innerHTML = options;
  element("env-resolver").value = state.settings.resolver_profile || "system";
  element("dns-resolver").value = state.settings.resolver_profile || "system";
  element("dns-profiles").innerHTML = table(
    ["Id", "Protocol", "Endpoint", "TLS required", "Fallback"],
    state.resolvers.map(function (profile) {
      return [profile.id, profile.protocol, profile.endpoint || profile.hostname || "system resolvers, read only", String(profile.verify_tls), profile.fallback_policy];
    })
  );
}

async function loadSettings() {
  const payload = await api("/api/settings");
  state.settings = payload.settings;
  element("st-url").value = payload.settings.default_url;
  element("st-profile").value = payload.settings.active_profile;
  element("st-resolver").value = payload.settings.resolver_profile;
  element("st-privacy").value = payload.settings.privacy_preset;
  element("st-level").value = payload.settings.diagnostics_level;
  element("st-private").checked = Boolean(payload.settings.private_browsing);
  element("env-url").value = payload.settings.default_url;
  element("env-privacy").value = payload.settings.privacy_preset;
  element("env-private").checked = Boolean(payload.settings.private_browsing);
}

function renderEnvironment(payload) {
  const snapshot = payload.snapshot;
  state.snapshot = snapshot;
  element("env-summary").innerHTML =
    badge("pipeline", snapshot.status, snapshot.status) +
    badge("state", snapshot.state.state, snapshot.state.state === "CONFLICT" ? "WARN" : "OK") +
    badge("consistency", snapshot.consistency.status, snapshot.consistency.status) +
    badge("duration", snapshot.duration_ms + " ms", "OK") +
    badge("geo source", snapshot.geo ? snapshot.geo.source : "not resolved", snapshot.geo ? "OK" : "WARN");
  element("env-pipeline").innerHTML = snapshot.stages.map(function (stage) {
    const kind = stage.status === "OK" ? "ok" : (stage.status === "SKIPPED" ? "skipped" : "failed");
    return '<span class="stage ' + kind + '">' + escapeHtml(stage.stage) + " | " + escapeHtml(stage.status) + '</span>';
  }).join("");
  const geo = snapshot.geo;
  element("env-location").innerHTML = geo ? kv([
    ["source", geo.source],
    ["mode", geo.mode],
    ["provider", geo.provider_id],
    ["latitude", geo.coordinate.latitude],
    ["longitude", geo.coordinate.longitude],
    ["accuracy meters", geo.coordinate.accuracy_m],
    ["confidence", geo.confidence],
    ["randomization seed", geo.seed === null ? "not applied" : geo.seed],
    ["signals", (geo.signals || []).join(", ")]
  ]) : '<div class="v muted">No geolocation fix was produced for this request.</div>';
  const zone = snapshot.timezone;
  element("env-timezone").innerHTML = zone ? kv([
    ["zone", zone.zone],
    ["mode", zone.mode],
    ["offset minutes", zone.offset_minutes],
    ["daylight saving active", String(zone.dst_active)],
    ["abbreviation", zone.abbreviation],
    ["controlled surfaces", zone.controlled_surfaces.length],
    ["not controlled", zone.uncontrolled_surfaces.length]
  ]) : '<div class="v muted">Timezone was not resolved.</div>';
  const locale = snapshot.locale;
  element("env-locale").innerHTML = locale ? kv([
    ["browser locale", locale.surfaces.browser_locale],
    ["language preference", locale.surfaces.language_preference],
    ["http language preference", locale.surfaces.http_language_preference],
    ["javascript surface", locale.surfaces.javascript_locale_surface],
    ["operating system locale", locale.surfaces.operating_system_locale]
  ]) : '<div class="v muted">Locale was not resolved.</div>';
  const dns = snapshot.dns;
  element("env-dns").innerHTML = dns ? kv([
    ["resolver", dns.active_resolver],
    ["protocol", dns.resolver_protocol],
    ["endpoint", dns.endpoint],
    ["tls status", dns.tls_status],
    ["fallback state", dns.fallback_state],
    ["system resolver unchanged", String(dns.system_resolver_unchanged)]
  ]) : '<div class="v muted">Browser default resolver behaviour, no probe performed.</div>';
  const policy = snapshot.policy;
  element("env-policy").innerHTML = kv([
    ["matched rules", policy.matched_rules.length],
    ["effective overrides", JSON.stringify(policy.effective_overrides)],
    ["precedence", "origin over subdomain over domain over browsing mode over global"],
    ["trace entries", policy.trace.length]
  ]);
  const invariants = snapshot.stages.filter(function (stage) { return stage.stage === "web_content_ready"; })[0];
  const list = invariants && invariants.output && invariants.output.invariants ? invariants.output.invariants : [];
  element("env-invariants").innerHTML = list.map(function (item) {
    return '<div class="k">' + escapeHtml(item.id) + '</div><div class="v"><span class="badge ' + (item.satisfied ? "ok" : "fail") + '">' +
      (item.satisfied ? "satisfied" : "violated") + '</span> ' + escapeHtml(item.statement) + '</div>';
  }).join("");
  const findings = snapshot.consistency.findings;
  element("env-consistency").innerHTML = findings.length === 0
    ? '<div class="v muted">No findings. ' + escapeHtml(snapshot.consistency.statement) + '</div>'
    : table(["Finding", "Severity", "Message", "Suggestion"], findings.map(function (item) {
      return [item.id, item.severity, item.message, item.suggestion];
    }));
  element("env-events").innerHTML = snapshot.events.map(function (event) {
    return "<div>" + escapeHtml(event.timestamp) + " | " + escapeHtml(event.severity) + " | " + escapeHtml(event.name) + " | " + escapeHtml(event.actor) + "</div>";
  }).join("");
}

async function runEnvironment() {
  setStatus("resolving environment", "warn");
  const query = new URLSearchParams({
    url: element("env-url").value,
    profile: element("env-profile").value,
    resolver: element("env-resolver").value,
    privacy: element("env-privacy").value,
    private: element("env-private").checked ? "true" : "false"
  });
  try {
    const payload = await api("/api/environment?" + query.toString());
    renderEnvironment(payload);
    setStatus("environment resolved", "ok");
  } catch (error) {
    setStatus("resolution failed", "fail");
    element("env-summary").innerHTML = badge("error", error.message, "FAIL");
  }
}

function collectProfile() {
  const languages = element("pf-languages").value.split(",").map(function (item) { return item.trim(); }).filter(Boolean);
  const profile = {
    name: element("pf-name").value.trim() || "unnamed",
    profile_version: 2,
    geolocation_mode: element("pf-mode").value,
    country: element("pf-country").value.trim().toUpperCase() || null,
    region: element("pf-region").value.trim() || null,
    city: element("pf-city").value.trim() || null,
    latitude: numberOrNull(element("pf-latitude").value),
    longitude: numberOrNull(element("pf-longitude").value),
    radius: numberOrNull(element("pf-radius").value) || 0,
    randomization: element("pf-randomization").value,
    randomization_seed: numberOrNull(element("pf-seed").value),
    timezone: element("pf-timezone").value.trim() || null,
    locale: element("pf-locale").value.trim() || null,
    languages: languages,
    webrtc_policy: element("pf-webrtc").value,
    block_physical_fallback: true
  };
  Object.keys(profile).forEach(function (key) {
    if (profile[key] === null) { delete profile[key]; }
  });
  return profile;
}

function fillProfile(profile) {
  element("pf-name").value = profile.name || "";
  element("pf-mode").value = profile.geolocation_mode || "manual";
  element("pf-country").value = profile.country || "";
  element("pf-region").value = profile.region || "";
  element("pf-city").value = profile.city || "";
  element("pf-latitude").value = profile.latitude === undefined ? "" : profile.latitude;
  element("pf-longitude").value = profile.longitude === undefined ? "" : profile.longitude;
  element("pf-radius").value = profile.radius === undefined ? "" : profile.radius;
  element("pf-randomization").value = profile.randomization || "none";
  element("pf-seed").value = profile.randomization_seed === undefined ? "" : profile.randomization_seed;
  element("pf-timezone").value = profile.timezone || "";
  element("pf-locale").value = profile.locale || "";
  element("pf-languages").value = (profile.languages || []).join(", ");
  element("pf-webrtc").value = profile.webrtc_policy || "default";
}

async function loadProfileIntoEditor() {
  const profileId = element("profile-select").value;
  setStatus("loading profile " + profileId, "warn");
  try {
    const payload = await api("/api/profiles/" + encodeURIComponent(profileId));
    state.selectedProfile = profileId;
    fillProfile(payload.profile);
    element("profile-result").innerHTML = badge("loaded", profileId, "OK");
    setStatus("profile loaded", "ok");
  } catch (error) {
    element("profile-result").innerHTML = badge("error", error.message, "FAIL");
    setStatus("profile load failed", "fail");
  }
}

async function validateProfile() {
  try {
    const payload = await api("/api/profiles/validate", { method: "POST", body: { profile: collectProfile() } });
    element("profile-result").innerHTML = badge("validation", payload.status, payload.status);
  } catch (error) {
    element("profile-result").innerHTML = badge("validation error", error.message, "FAIL");
  }
}

async function saveProfile() {
  const profile = collectProfile();
  try {
    const payload = await api("/api/profiles/" + encodeURIComponent(profile.name), { method: "PUT", body: { profile: profile } });
    element("profile-result").innerHTML = badge("saved", payload.saved.id, "OK") +
      '<div class="muted">stored at ' + escapeHtml(payload.saved.path) + '</div>';
    await loadProfiles();
    setStatus("profile saved", "ok");
  } catch (error) {
    element("profile-result").innerHTML = badge("save failed", error.message, "FAIL");
  }
}

async function deleteProfile() {
  const profileId = element("profile-select").value;
  try {
    const payload = await api("/api/profiles/" + encodeURIComponent(profileId), { method: "DELETE" });
    element("profile-result").innerHTML = badge("deleted", payload.id, "OK");
    await loadProfiles();
  } catch (error) {
    element("profile-result").innerHTML = badge("delete failed", error.message, "FAIL");
  }
}

async function exportProfile() {
  const profileId = element("profile-select").value;
  try {
    const payload = await api("/api/profiles/" + encodeURIComponent(profileId) + "/export");
    element("import-payload").value = payload.payload;
    element("profile-result").innerHTML = badge("exported", profileId, "OK") + '<div class="muted">payload placed in the import area</div>';
  } catch (error) {
    element("profile-result").innerHTML = badge("export failed", error.message, "FAIL");
  }
}

async function importProfile() {
  const payloadText = element("import-payload").value;
  const dryRun = element("import-dry").checked;
  try {
    const payload = await api("/api/profiles/import", {
      method: "POST",
      body: { payload: payloadText, profile_id: element("pf-name").value.trim() || null, dry_run: dryRun }
    });
    element("import-result").innerHTML = badge(dryRun ? "validated" : "activated", String(payload.activated), "OK") +
      '<div class="muted">migrations applied: ' + payload.migrations_applied.length + '</div>';
    if (!dryRun) { await loadProfiles(); }
  } catch (error) {
    element("import-result").innerHTML = badge("import failed", error.message, "FAIL");
  }
}

async function runProbe() {
  setStatus("probing resolver", "warn");
  try {
    const payload = await api("/api/dns/probe", {
      method: "POST",
      body: {
        resolver: element("dns-resolver").value,
        name: element("dns-name").value,
        type: element("dns-type").value
      }
    });
    const probe = payload.probe;
    const rows = (probe.records || []).map(function (record) {
      return [record.name, record.type, String(record.ttl), typeof record.value === "string" ? record.value : JSON.stringify(record.value)];
    });
    element("dns-result").innerHTML =
      badge("probe", probe.status, probe.status) +
      badge("rcode", probe.rcode, probe.status) +
      badge("latency", probe.latency_ms + " ms", probe.status) +
      (rows.length ? table(["Name", "Type", "TTL", "Value"], rows) : '<div class="muted">' + escapeHtml((probe.notes || []).join(" | ")) + '</div>');
    element("dns-integrity").innerHTML = kv([
      ["system resolver modified", String(payload.diagnostics.system_resolver_unchanged === false)],
      ["integrity statement", payload.diagnostics.system_resolver_unchanged ? "operating system resolver configuration unchanged" : "change detected, investigate"],
      ["resolver protocol", payload.diagnostics.resolver_protocol],
      ["tls status", payload.diagnostics.tls_status],
      ["fallback", payload.diagnostics.fallback_state]
    ]);
    setStatus("probe complete", "ok");
  } catch (error) {
    element("dns-result").innerHTML = badge("probe failed", error.message, "FAIL");
    setStatus("probe failed", "fail");
  }
}

async function loadDiagnostics() {
  const level = element("diag-level").value;
  try {
    const payload = await api("/api/diagnostics?level=" + encodeURIComponent(level));
    element("diag-result").innerHTML = badge("level", payload.level, "OK") +
      badge("consistency", payload.report.environment.consistency.status, payload.report.environment.consistency.status);
    element("diag-json").textContent = JSON.stringify(payload.report, null, 2);
    setStatus("diagnostic report generated", "ok");
  } catch (error) {
    element("diag-result").innerHTML = badge("error", error.message, "FAIL");
  }
}

async function loadConsistency() {
  const query = new URLSearchParams({ profile: element("env-profile").value, resolver: element("env-resolver").value });
  const payload = await api("/api/consistency?" + query.toString());
  element("diag-result").innerHTML = badge("consistency", payload.consistency.status, payload.consistency.status) +
    badge("highest severity", payload.consistency.highest_severity, payload.consistency.highest_severity);
  element("diag-json").textContent = JSON.stringify(payload.consistency, null, 2);
}

async function loadScans() {
  const payload = await api("/api/scans");
  element("diag-result").innerHTML = table(["Scanner", "Status", "Violations", "Exempted files"], payload.scans.map(function (item) {
    return [item.scanner, item.status, item.violations, item.exempted_files];
  }));
  element("platform-scans").innerHTML = element("diag-result").innerHTML;
}

async function loadRequests() {
  const payload = await api("/api/requests");
  element("diag-result").innerHTML = table(["Method", "Path", "Status", "Duration ms"], payload.requests.map(function (item) {
    return [item.method, item.path, item.status, item.duration_ms];
  }));
}

async function loadIdentity() {
  const payload = await api("/api/identity");
  element("platform-legibility").innerHTML = table(["Size", "Eye diameter", "Eye separation", "Result"], payload.report.eye_visibility.map(function (item) {
    return [item.size + " px", item.eye_diameter_px + " px", item.eye_separation_px + " px", item.eyes_distinguishable ? "distinguishable" : "not distinguishable"];
  }));
  element("platform-endpoints").innerHTML = table(["Method", "Path", "Purpose"], endpoints);
}

async function saveSettings() {
  const settings = {
    default_url: element("st-url").value,
    active_profile: element("st-profile").value,
    resolver_profile: element("st-resolver").value,
    privacy_preset: element("st-privacy").value,
    diagnostics_level: element("st-level").value,
    private_browsing: element("st-private").checked
  };
  try {
    const payload = await api("/api/settings", { method: "PUT", body: { settings: settings } });
    state.settings = payload.settings;
    element("st-result").innerHTML = badge("saved", payload.saved_at, "OK");
    await loadSettings();
    setStatus("settings saved", "ok");
  } catch (error) {
    element("st-result").innerHTML = badge("save failed", error.message, "FAIL");
  }
}

async function loadWebrtc() {
  const payload = await api("/api/webrtc");
  element("st-webrtc").innerHTML = table(["Policy", "Host candidates suppressed", "Relay only", "Limitation"], payload.policies.map(function (item) {
    const preferences = item.preferences || {};
    return [
      item.policy,
      String(preferences["media.peerconnection.ice.no_host"] === true),
      String(preferences["media.peerconnection.ice.relay_only"] === true),
      item.limitation_statement
    ];
  }));
}

const SAMPLE_THEME = {
  manifest_version: 2,
  name: "Neon Grid",
  version: "1.2.0",
  type: "theme",
  theme: {
    colors: {
      frame: "#05060A",
      toolbar: "#12142B",
      tab_selected: ["#FF2D3F", "#A855F7"],
      toolbar_text: "#F5F7FF",
      popup: "#12142B",
      popup_text: "#F5F7FF"
    },
    images: { theme_frame: "header.png" }
  }
};

function gradientCss(gradient) {
  if (!gradient || !gradient.stops || gradient.stops.length < 2) { return "linear-gradient(135deg, #0B0C0E, #1B0B2E)"; }
  return "linear-gradient(" + (gradient.angle_degrees || 135) + "deg, " + gradient.stops.join(", ") + ")";
}

async function loadAddons() {
  const listing = await api("/api/extensions");
  element("addons-summary").innerHTML =
    badge("recorded", listing.count, "OK") +
    badge("active theme", listing.active_theme || "none", listing.active_theme ? "OK" : "WARN") +
    badge("signature state", listing.signature_state, "WARN") +
    badge("engine", listing.runtime.engine_version, "OK");
  element("addons-list").innerHTML = listing.extensions.length === 0
    ? '<div class="v muted">No add-on has been recorded yet.</div>'
    : table(["Identifier", "Name", "Type", "Compatibility", "Signature", "Notice acknowledged"], listing.extensions.map(function (entry) {
        return [entry.id, entry.name, entry.type, entry.compatibility_level + " " + entry.compatibility_score, entry.signature, String(entry.notice_acknowledged)];
      }));
  const themes = await api("/api/themes");
  const active = themes.active_theme;
  element("addons-active-theme").innerHTML =
    '<div class="gradient-preview" style="background:' + gradientCss(active.gradient) + '"></div>' +
    '<div class="v">' + escapeHtml(active.name || active.id) + ' | source ' + escapeHtml(active.source) + ' | stops ' +
    escapeHtml(active.gradient ? active.gradient.stops.join(" ") : "product default") + '</div>';
  if (!themes.themes.length) {
    element("addons-theme-detail").innerHTML = '<div class="v muted">No theme recorded. Inspect a desktop theme manifest to see the palette translation.</div>';
    return;
  }
  element("addons-theme-detail").innerHTML = table(["Theme", "Palette keys", "Gradient", "Findings"], themes.themes.map(function (theme) {
    return [theme.name, String(theme.declared_color_keys.length), theme.gradient.stops.join(" "), theme.findings.map(function (item) { return item.code; }).join(", ")];
  })) + '<div class="row">' + themes.themes.map(function (theme) {
    return '<button data-theme="' + escapeHtml(theme.id) + '" class="theme-activate">Activate ' + escapeHtml(theme.name) + '</button>';
  }).join("") + '</div>';
  Array.prototype.forEach.call(document.querySelectorAll(".theme-activate"), function (button) {
    button.addEventListener("click", async function () {
      await api("/api/themes/active", { method: "PUT", body: { id: button.getAttribute("data-theme") } });
      setStatus("theme activated", "ok");
      await loadAddons();
    });
  });
}

async function loadCompatMatrix() {
  const payload = await api("/api/compat/firefox-desktop");
  element("addons-matrix").innerHTML = table(["Surface", "Level", "Note"], payload.sections.map(function (entry) {
    return [entry.section, entry.level, entry.note || ""];
  })) + '<p class="muted">' + escapeHtml(payload.install_notice) + '</p>';
}

function manifestFromEditor() {
  return JSON.parse(element("addons-manifest").value);
}

function renderCompatibility(payload) {
  const compatibility = payload.compatibility;
  element("addons-result").innerHTML =
    badge("level", compatibility.level, compatibility.level === "COMPATIBLE" ? "OK" : "WARN") +
    badge("score", compatibility.score, "WARN") +
    '<div class="notice-block">' + escapeHtml(payload.notice) + '</div>' +
    table(["Surface", "Level", "Note"], compatibility.sections.concat(compatibility.permissions).map(function (entry) {
      return [entry.section || entry.permission, entry.level, entry.note || ""];
    }));
}

async function inspectAddon() {
  try {
    const payload = await api("/api/extensions/inspect", { method: "POST", body: { manifest: manifestFromEditor() } });
    renderCompatibility(payload);
    if (payload.theme && payload.theme.gradient) {
      element("addons-active-theme").innerHTML =
        '<div class="gradient-preview" style="background:' + gradientCss(payload.theme.gradient) + '"></div>' +
        '<div class="v">preview of ' + escapeHtml(payload.theme.name) + ' | stops ' + escapeHtml(payload.theme.gradient.stops.join(" ")) + '</div>';
    }
    setStatus("manifest inspected", "ok");
  } catch (error) {
    element("addons-result").innerHTML = badge("error", error.message, "FAIL");
  }
}

async function installAddon() {
  try {
    const payload = await api("/api/extensions/install", {
      method: "POST",
      body: { manifest: manifestFromEditor(), acknowledged: element("addons-ack").checked }
    });
    element("addons-result").innerHTML =
      badge("recorded", payload.installed.id, "OK") +
      badge("compatibility", payload.installed.compatibility_level, "WARN") +
      badge("signature", payload.installed.signature, "WARN") +
      '<div class="notice-block">' + escapeHtml(payload.notice) + '</div>';
    setStatus("add-on recorded", "ok");
    await loadAddons();
  } catch (error) {
    element("addons-result").innerHTML = badge("refused", error.message, "FAIL") +
      '<div class="v muted">Installations require the compatibility notice to be acknowledged. Prohibited permissions are refused regardless of acknowledgement.</div>';
  }
}

function selectView(view) {
  Array.prototype.forEach.call(document.querySelectorAll(".tab"), function (tab) {
    tab.classList.toggle("active", tab.getAttribute("data-view") === view);
  });
  Array.prototype.forEach.call(document.querySelectorAll(".view"), function (section) {
    section.classList.toggle("active", section.id === "view-" + view);
  });
  if (view === "platform") { loadIdentity(); loadScans(); }
  if (view === "settings") { loadWebrtc(); }
  if (view === "dns") { loadResolvers(); }
  if (view === "addons") { loadCompatMatrix(); loadAddons(); }
}

function wire() {
  Array.prototype.forEach.call(document.querySelectorAll(".tab"), function (tab) {
    tab.addEventListener("click", function () { selectView(tab.getAttribute("data-view")); });
  });
  element("env-run").addEventListener("click", runEnvironment);
  element("profile-load").addEventListener("click", loadProfileIntoEditor);
  element("profile-new").addEventListener("click", function () {
    fillProfile({ name: "new-profile", profile_version: 2, geolocation_mode: "manual", randomization: "none", block_physical_fallback: true });
    element("profile-result").innerHTML = badge("editor", "new profile draft", "WARN");
  });
  element("profile-save").addEventListener("click", saveProfile);
  element("profile-delete").addEventListener("click", deleteProfile);
  element("profile-export").addEventListener("click", exportProfile);
  element("profile-validate").addEventListener("click", validateProfile);
  element("import-run").addEventListener("click", importProfile);
  element("dns-probe").addEventListener("click", runProbe);
  element("diag-run").addEventListener("click", loadDiagnostics);
  element("diag-consistency").addEventListener("click", loadConsistency);
  element("diag-scans").addEventListener("click", loadScans);
  element("diag-requests").addEventListener("click", loadRequests);
  element("st-save").addEventListener("click", saveSettings);
  element("st-reload").addEventListener("click", loadSettings);
  element("addons-sample").addEventListener("click", function () {
    element("addons-manifest").value = JSON.stringify(SAMPLE_THEME, null, 2);
  });
  element("addons-inspect").addEventListener("click", inspectAddon);
  element("addons-install").addEventListener("click", installAddon);
  element("profile-select").addEventListener("change", function () { element("profile-result").innerHTML = ""; });
}

async function start() {
  wire();
  await loadHealth();
  await loadSettings();
  await loadProfiles();
  await loadResolvers();
  await runEnvironment();
}

start();
