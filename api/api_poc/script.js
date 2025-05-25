// script.js
let api_protocol = 'http';
let api_host = '192.168.188.103';
let api_port = '80';
let api_basepath = '/api/v1';
let current_api = null;
let status_interval = 10000;

const api_data = new Map([
  ["sys_config", { mode: "config", parent_key: "system", text: "Machine", url: "/system/config", exclude_keys: ['machinerotators', 'balldrivers', 'ballstirrers', 'ballfeeders'] }],
  ["bd_config", { mode: "config", parent_key: "balldrivers", text: "Ball Drivers", url: "/balldrivers/config", exclude_keys: [] }],
  ["bf_config", { mode: "config", parent_key: "ballfeeders", text: "Ball Feeders", url: "/ballfeeders/config", exclude_keys: [] }],
  ["bs_config", { mode: "config", parent_key: "ballstirrers", text: "Ball Stirrers", url: "/ballstirrers/config", exclude_keys: [] }],
  ["mr_config", { mode: "config", parent_key: "machinerotators", text: "Machine Rotators", url: "/machinerotators/config", exclude_keys: [] }],
]);
const api_test_routines = new Map([
  ["balldrivers", [
    { text: "start", description: "start the stirrer with its current settings", url_ext: "/start", method: "POST"},
    { text: "stop", description: "stop the stirrer", url_ext: "/stop", method: "POST"},
  ]],
  ["ballstirrers", [
    { text: "start", description: "start the stirrer with its current settings", url_ext: "/start", method: "POST"},
    { text: "stop", description: "stop the stirrer", url_ext: "/stop", method: "POST"},
  ]],
  ["machinerotators", [
    { text: "start", description: "start the rotator with its current settings", url_ext: "/start", method: "POST"},
    { text: "stop", description: "stop the rotator", url_ext: "/stop", method: "POST"},
  ]],
  ["ballfeeders", [
    { text: "retract", description: "move the feeder back a bit", url_ext: "/retract", method: "POST"},
    { text: "extend", description: "move the feeder forward a bit", url_ext: "/extend", method: "POST"},
  ]]
])

const contentSidebar = document.getElementById('content-sidebar');
const navSidebar = document.getElementById('nav-sidebar');
const configContainer = document.getElementById('mode-container');
const statusContainer = document.getElementById('footer-container');
const machineStatusContainer = document.getElementById('machinestatus-placeholder');

// Globale Variable für die JSON-Daten
let apiData = null; //this is the full data returned by the API
let displayData = null; // this is the data actually displayed in the workarea, which might be a subset of the full API data

// Funktion zum Abrufen der JSON-Daten von der REST-API
async function fetchJsonDataFromApi(api_url) {
  try {
    const url = `${api_protocol}://${api_host}:${api_port}${api_basepath}${api_url}`;
    const response = await fetch(url);
    const data = await response.json();
    apiData = data.data; // JSON-Daten in der globalen Variable speichern
  } catch (error) {
    throw error; // Fehler weitergeben, damit er im Aufrufer behandelt werden kann
  }
}


async function getMachineStatus() {
  try {
    renderAppStatus('Fetching machine status...');
    await fetchJsonDataFromApi('/system/status');
    const statusHtml = `
      <div>Mode: ${apiData.mode}</div>
      <div>Status: ${apiData.status}</div>
      <div>Next Shot in Cycle: ${apiData.shot_cycle.next_shot_index}/${apiData.shot_cycle.total_shots}</div>
    `;
    machineStatusContainer.innerHTML = statusHtml;
    renderAppStatus('OK');
  } catch (error) {
    machineStatusContainer.innerHTML = 'Fehler beim Abrufen des Status: ' + error;
    renderAppStatus('Fehler beim Abrufen des Status:', error);
  }
}

function fillNavigationSidebar(mode) {
  clearSidebar(navSidebar);
  api_data.forEach((value, key) => {
    if (value.mode === mode) {
      addSidebarItem(navSidebar, value.text, key, selectNavigationSidebarItem, "");
    };
  });
  selectFirstSidebarItem(navSidebar);
}
/**
 * Is called when an item is clicked in the navigation sidebar.
 * Activates the item and shows the corresponding config in the content area.
 *
 * @param {HTMLElement} sidebar The navigation sidebar element.
 * @param {HTMLElement} item The item to select.
 */
function selectNavigationSidebarItem(sidebar, item) {
  const activeItem = sidebar.querySelector('.active');
  if (activeItem) {
    activeItem.classList.remove('active');
  }
  item.classList.add('active');
  // Hier kannst du auch die versteckten Daten auslesen, wenn du sie benötigst
  const value = item.dataset.value;
  // Show the config for the selected key
  console.log('Selected Sidebar-Item:', value);
  current_api = api_data.get(value);
  getSystemConfig();
}

// Funktion zum Umschalten zwischen den Betriebsmodi
function switchMode(mode) {
  // Hier wird die jeweilige Bedienung des gewählten Modus implementiert
  console.log(`Modus gewechselt zu: ${mode}`);
  // Setze den aktiven Modus
  const buttons = document.querySelectorAll('.mode-switcher');
  buttons.forEach((button) => {
    button.classList.remove('active');
  });
  const activeButton = document.querySelector(`.mode-switcher[data-mode="${mode}"]`);
  activeButton.classList.add('active');

  fillNavigationSidebar(mode);

  switch (mode) {
    case 'config':
      configContainer.style.display = 'block';
      getSystemConfig();
      break;
    case 'direct':
      configContainer.style.display = 'none';
      break;
    case 'program':
      configContainer.style.display = 'none';
      break;
    default:
      configContainer.style.display = 'none';
  }
}

// Event-Listener für die Umschaltung zwischen den Betriebsmodi
document.querySelectorAll('.mode-switcher').forEach((button) => {
  button.addEventListener('click', (event) => {
    event.preventDefault();
    const mode = button.getAttribute('data-mode');
    switchMode(mode);
  });
});

// Funktion, um die Sidebar zu leeren
function clearSidebar(sidebar) {
  sidebar.innerHTML = '';
}

async function callApiMethod(url, method, data) {
  try {
    const fullUrl = `${api_protocol}://${api_host}:${api_port}${api_basepath}${url}`;
    const response = await fetch(fullUrl, {
      method: method,
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });
    const apiData = await response.json();
    return apiData;
  } catch (error) {
    throw error; // Fehler weitergeben, damit er im Aufrufer behandelt werden kann
  }
}
// Funktion, um ein einzelnes Sidebar-Item hinzuzufügen
function addSidebarItem(sidebar, text, value, onclick_function, parent_key) {
  const sidebarButton = document.createElement('BUTTON');
  sidebarButton.textContent = text;
  sidebarButton.classList.add('sidebar-button');
  sidebarButton.dataset.value = value; // Versteckte Daten im data-Attribut speichern
  sidebarButton.addEventListener('click', () => {
    onclick_function(sidebar, sidebarButton);
  });
  // add function buttons
  if (api_test_routines.has(parent_key)) {
    const routines = api_test_routines.get(parent_key);
    routines.forEach((routine) => {
      var funcButton = document.createElement('BUTTON');
      funcButton.textContent = routine.text;
      funcButton.classList.add('function-button');
      funcButton.dataset.value = value; // Versteckte Daten im data-Attribut speichern
      funcButton.addEventListener('click', () => {
        callApiMethod('/'+parent_key+'/'+value+routine.url_ext, routine.method, routine.data);
      });
      sidebarButton.appendChild(funcButton);
    })

  }
  sidebar.appendChild(sidebarButton);
}

// Funktion, um ein Sidebar-Item auszuwählen
function selectConfigSidebarItem(sidebar, item) {
  const activeItem = sidebar.querySelector('.active');
  if (activeItem) {
    activeItem.classList.remove('active');
  }
  item.classList.add('active');
  // Hier kannst du auch die versteckten Daten auslesen, wenn du sie benötigst
  const value = item.dataset.value;
  // Show the config for the selected key
  console.log('Selected Sidebar-Item:', value);
  if (value in apiData) {
    renderConfig(apiData[value]); // Rendere die Konfiguration();
  }
}
function selectFirstSidebarItem(sidebar) {
  const firstItem = sidebar.querySelector('.sidebar-button');
  if (firstItem) {
    firstItem.classList.add('active');
    firstItem.click();
  }
}
/**
 * Füllt die Sidebar mit den Keys aus zurück erhaltenen API-Daten (ausgenommen jener,
 * die unterdrückt werden sollen) und wählt das erste Item automatisch aus.
 * @param {Object} data - Das Daten-Objekt, das die Keys enthält, die in der
 * Sidebar dargestellt werden sollen.
 */
function fillContentSidebar(data) {
  clearSidebar(contentSidebar);
  for (const key in data) {
    if (!current_api.exclude_keys.includes(key)) {
      addSidebarItem(contentSidebar, key, key, selectConfigSidebarItem, current_api.parent_key);
    }
  }
  // select the first item by default
  selectFirstSidebarItem(contentSidebar);
}

// Funktion zum Abrufen der Konfiguration
async function getSystemConfig() {
  renderAppStatus('Fetching configuration...');
  await fetchJsonDataFromApi(current_api.url)
    .then(() => loadConfig(apiData))
    .then(() => renderAppStatus('OK'))
    .catch(error => renderAppStatus('Fehler beim Abrufen der Konfiguration:', error));
}

function loadConfig(config) {
  fillContentSidebar(config);
}

/**
 * Renders a status message in the status container, optionally with an error.
 * If an error is provided, it will be logged to the console as well.
 * @param {string} message The status message to display. If it comes with an error, should end with a colon (:) but no trailing space.
 * @param {Error} [error] An optional error object to log to the console and include in the status message.
 */
function renderAppStatus(message, error) {
  if (error) {
    console.error(message, error);
  }
  statusContainer.innerHTML = message + (error ? ' ' + error : '');
}
// Funktion zum Rendern der Konfiguration
function renderConfig(jsonObject) {
  configContainer.innerHTML = '';
  displayData = jsonObject;
  const table = document.createElement('table');
  table.className = 'config-table';

  if (typeof jsonObject === 'object') {
    Object.keys(jsonObject).sort().forEach(key => {
      const value = jsonObject[key];
      table.appendChild(renderValueAsTableRow(key, value));
    });
  } else {
    table.appendChild(renderValueAsTableRow('value', jsonObject));
  }
  configContainer.appendChild(table);
}

function renderValueAsTableRow(key, value) {
  const row = document.createElement('tr');
  row.innerHTML = `<th>${key}</th><td>${renderValue(value, key)}</td>`;
  return row;
}

function renderValue(value, key) {
  if (Array.isArray(value)) {
    return renderArray(value);
  } else if (typeof value === 'object') {
    return renderObject(value);
  } else {
    return `<input type="text" data-key="${key}" value="${value}" disabled> <button onclick="editValue('${key}')">Edit</button>`;
  }
}

function renderArray(array) {
  const html = array.map((item, index) => {
    return `<tr><td>[${index}]</td><td>${renderValue(item)}</td></tr>`;
  }).join('');
  return `<table>${html}</table>`;
}

function renderObject(obj) {
  const html = Object.keys(obj).map(key => {
    return `<tr><td>${key}</td><td>${renderValue(obj[key])}</td></tr>`;
  }).join('');
  return `<table>${html}</table>`;
}

function editValue(key) {
  const inputElement = document.querySelector(`[data-key="${key}"]`);
  const value = inputElement.value;
  inputElement.disabled = false;
  inputElement.id = `new-value-${key}`;
  const cancelButton = document.createElement('button');
  cancelButton.onclick = function () { cancelEdit(key); };
  cancelButton.innerHTML = 'Abbrechen';
  inputElement.parentElement.appendChild(cancelButton);
  const saveButton = document.createElement('button');
  saveButton.onclick = function () { saveNewValue(key); };
  saveButton.innerHTML = 'Speichern';
  inputElement.parentElement.appendChild(saveButton);
}

function saveNewValue(key) {
  const newValue = document.getElementById(`new-value-${key}`).value;
  displayData[key] = newValue; //adopt changes
  console.log(`Neuer Wert für ${key}: ${newValue}`);
  cancelEdit(key);
}

function cancelEdit(key) {
  const element = document.getElementById(`new-value-${key}`);
  element.parentElement.innerHTML = renderValue(displayData[key], key);
}
getMachineStatus();
setInterval(getMachineStatus, status_interval);

