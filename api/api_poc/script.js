// script.js
let api_protocol = 'http';
let api_host = '192.168.188.103';
let api_port = '80';
let api_basepath = '/api/v1';
let current_api = null; // API info for the current menu item
let status_interval = 10000;

const menu_api_map = new Map([
  ["sys_config", { mode: "config", parent_key: "system", text: "Machine", url: "/system/config", exclude_keys: ['machinerotators', 'balldrivers', 'ballstirrers', 'ballfeeders'] }],
  ["bd_config", { mode: "config", parent_key: "balldrivers", text: "Ball Drivers", url: "/balldrivers/config", exclude_keys: [] }],
  ["bf_config", { mode: "config", parent_key: "ballfeeders", text: "Ball Feeders", url: "/ballfeeders/config", exclude_keys: [] }],
  ["bs_config", { mode: "config", parent_key: "ballstirrers", text: "Ball Stirrers", url: "/ballstirrers/config", exclude_keys: [] }],
  ["mr_config", { mode: "config", parent_key: "machinerotators", text: "Machine Rotators", url: "/machinerotators/config", exclude_keys: [] }],
]);
const api_test_routines = new Map([
  ["balldrivers/[i]", [
    { text: "start", description: "start the stirrer with its current settings", url_ext: "/start", method: "POST"},
    { text: "stop", description: "stop the stirrer", url_ext: "/stop", method: "POST"},
  ]],
  ["balldrivers/[i]/motors/[i]", [
    { text: "start", description: "start the motor in positive direction (this should accelerate the ball out of the machine)", url_ext: "/start", method: "POST"},
    { text: "stop", description: "stop the motor", url_ext: "/stop", method: "POST"},
  ]],
  ["ballstirrers/[i]", [
    { text: "start", description: "start the stirrer with its current settings", url_ext: "/start", method: "POST"},
    { text: "stop", description: "stop the stirrer", url_ext: "/stop", method: "POST"},
  ]],
  ["ballstirrers/[i]/motors/[i]", [
    { text: "start", description: "start the motor with its current settings", url_ext: "/start", method: "POST"},
    { text: "stop", description: "stop the motor", url_ext: "/stop", method: "POST"},
  ]],
  ["machinerotators/[i]", [
    { text: "rotate home", description: "move the rotator into neutral position", url_ext: "/rotate_home", method: "POST"},
    { text: "rotate min", description: "turn the rotator to its min rotation", url_ext: "/rotate_min", method: "POST"},
    { text: "rotate max", description: "turn the rotator to its max rotation", url_ext: "/rotate_max", method: "POST"},
  ]],
  ["machinerotators/[i]/motors/[i]", [
    { text: "rotate home", description: "move the rotator motor into neutral position", url_ext: "/rotate_home", method: "POST"},
    { text: "rotate min", description: "turn the motor to its min rotation", url_ext: "/rotate_min", method: "POST"},
    { text: "rotate max", description: "turn the motor to its max rotation", url_ext: "/rotate_max", method: "POST"},
    { text: "left", description: "turn the motor 5° to the left", url_ext: "/rotate", method: "PUT", data: { angle: -5.0 } },
    { text: "right", description: "turn the motor 5° to the right", url_ext: "/rotate", method: "PUT", data: { angle: 5.0 } },
  ]],
  ["ballfeeders/[i]", [
    { text: "prepare", description: "set current position as mounting position and move from here into waiting position", url_ext: "/prepare", method: "POST"},
    { text: "dispense", description: "dispense one ball (perform the full action cycle)", url_ext: "/dispense", method: "POST"},
    { text: "stop", description: "immediately stop the feeder motor(s)", url_ext: "/stop", method: "POST"},
  ]],
  ["ballfeeders/[i]/motors/[i]", [
    { text: "step +", description: "run one step into positive direction", url_ext: "/rotate", method: "PUT", data: { angle: 5.0 } },
    { text: "step -", description: "run one step into negative direction", url_ext: "/rotate", method: "PUT", data: { angle: -5.0 } },
  ]],
])

const contentSidebar = document.getElementById('content-sidebar');
const navSidebar = document.getElementById('nav-sidebar');
const configContainer = document.getElementById('mode-container');
const statusContainer = document.getElementById('footer-container');
const machineStatusContainer = document.getElementById('machinestatus-placeholder');

// Globale Variable für die JSON-Daten
/**
 * Stores the full data returned by the last API call.
 * @type {Object|null}
 */
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
  menu_api_map.forEach((value, key) => {
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
  const value = item.dataset.apiDataKey;
  // Show the config for the selected key
  console.log('Selected Sidebar-Item:', value);
  current_api = menu_api_map.get(value);
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
function addSidebarItem(sidebar, text, value, onclick_function, parentMenuKey) {
  const menuKey = parentMenuKey + '/' + value;
  const menuSearchKey = parentMenuKey + '/' + (Number.parseInt(value).toString()==value ? '[i]' : value);
  const sidebarButton = document.createElement('BUTTON');
  sidebarButton.textContent = text;
  sidebarButton.classList.add('sidebar-button');
  sidebarButton.dataset.apiDataKey = value; // Data-Attribut für den Key in den API-Daten
  sidebarButton.dataset.menuKey = menuKey; // Der eigentliche Key für diesen Menüpunkt
  sidebarButton.dataset.menuSearchKey = menuSearchKey; // Der Key zum Suchen in den API-Test-Routinen
  sidebarButton.addEventListener('click', () => {
    onclick_function(sidebar, sidebarButton);
  });
  // add function buttons
  if (api_test_routines.has(menuSearchKey)) {
    const routines = api_test_routines.get(menuSearchKey);
    routines.forEach((routine) => {
      var funcButton = document.createElement('BUTTON');
      funcButton.textContent = routine.text;
      funcButton.classList.add('function-button');
      funcButton.addEventListener('click', () => {
        callApiMethod('/'+menuKey+routine.url_ext, routine.method, routine.data);
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
  const dataKey = item.dataset.apiDataKey;
  const menuKey = item.dataset.menuKey;
  const menuSearchKey = item.dataset.menuSearchKey;
  // Show the config for the selected key
  console.log('Selected Sidebar-Item:', dataKey);
  if (dataKey in apiData) {
    renderConfig(apiData[dataKey], menuKey, menuSearchKey); // Rendere die Konfiguration();
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
// TopLevel-Funktion zum Rendern der Konfiguration, d.h. es wird für dieses Element kein key angezeit, 
// da dieser in der Sidebar ausgewählt wird.
function renderConfig(jsonObject, parentMenuKey, parentMenuSearchKey) {
  configContainer.innerHTML = '';
  displayData = jsonObject;
  const table = document.createElement('table');
  table.className = 'config-table';

  if (typeof jsonObject === 'object') {
    Object.keys(jsonObject).sort().forEach(key => {
      const value = jsonObject[key];
      table.appendChild(renderValueAsTableRow(key, value, parentMenuKey + '/' + key, parentMenuSearchKey + '/' + key));
    });
  }
  else if (Array.isArray(jsonObject)) {
    jsonObject.keys(jsonObject).forEach(key => {
      const value = jsonObject[key];
      table.appendChild(renderValueAsTableRow(`[${key}]`, value, parentMenuKey + '/' + key, parentMenuSearchKey + '/[i]'));
    });
  } else {
    table.appendChild(renderValueAsTableRow('value', jsonObject, parentMenuKey, parentMenuSearchKey));
  }
  configContainer.appendChild(table);
}

function renderValueAsTableRow(key, value, menuKey, menuSearchKey) {
  const row = document.createElement('tr');
  const th = document.createElement('th');
  th.textContent = key;
  row.appendChild(th);
  const td = document.createElement('td');
  td.appendChild(renderValue(value, key, menuKey, menuSearchKey))
  row.appendChild(td);

  if (api_test_routines.has(menuSearchKey)) {
    const routines = api_test_routines.get(menuSearchKey);
    routines.forEach(routine => {
      var funcButton = document.createElement('BUTTON');
      funcButton.textContent = routine.text;
      funcButton.classList.add('function-button');
      funcButton.addEventListener('click', () => {
        callApiMethod('/'+menuKey+routine.url_ext, routine.method, routine?.data);
      });
      th.appendChild(funcButton);
    });
  }
  return row;
}

/**
 * Renders any config value in html - just the value, the key is only used for assignment of the input.
 *
 * If the value is an array, it will be rendered as a table with the indices as headers.
 * If the value is an object, it will be rendered as a table iwth the keys as headers.
 * Otherwise, it will be rendered as an input field with an edit button.
 *
 * @param {HTMLElement} parentElement The element to render inside of.
 * @param {*} value The value to render.
 * @param {string} key The key of the value in the parent object.
 * @param {string} menuKey The key of the parent menu item.
 * @param {string} menuSearchKey The search key of the parent menu item.
 * @return {HTMLElement} The rendered HTML.
 */
function renderValue(value, key, menuKey, menuSearchKey) {
  if (Array.isArray(value)) {
    return renderArray(value, menuKey, menuSearchKey);
  } else if (typeof value === 'object') {
    return renderObject(value, menuKey, menuSearchKey);
  } else {
    const spanElement = document.createElement('span');
    const inputElement = document.createElement('input');
    inputElement.type = 'text';
    inputElement.value = value;
    inputElement.dataset.key = key; // Set the key as a data attribute for easy access
    inputElement.disabled = true; // Disable the input field by default
    spanElement.appendChild(inputElement);
    // add function keys
    var buttonElement = document.createElement('button');
    buttonElement.textContent = 'Edit';
    buttonElement.addEventListener('click', () => {
      editValue(key);
    });
    spanElement.appendChild(buttonElement);
    return spanElement;
  }
}

/**
 * Renders a full array as a table with the indices as headers.
 * @param {Array} array The array to render.
 * @param {string} parentMenuKey The key of the parent menu item.
 * @param {string} parentMenuSearchKey The search key of the parent menu item.
 * @return {HTMLTableElement} The resulting HTML table element.
 */
function renderArray(array, parentMenuKey, parentMenuSearchKey) {
  const tbl = document.createElement('table');
  for (let i = 0; i < array.length; i++) {
    const menuKey = parentMenuKey + '/' + i.toString();
    const menuSearchKey = parentMenuSearchKey + '/[i]';
    const tr = renderValueAsTableRow(`[${i}]`, array[i], menuKey, menuSearchKey);
    tbl.appendChild(tr);
  }
  return tbl;
}

/**
 * Renders a full object as an HTML table with one row per key.
 * @param {Object} obj - The object to be rendered.
 * @param {string} parentMenuKey - The key for the parent menu item, used for hierarchical rendering.
 * @param {string} parentMenuSearchKey - The search key for the parent menu item, used for hierarchical rendering.
 * @return {HTMLTableElement} The constructed table representing the object.
 */

function renderObject( obj, parentMenuKey, parentMenuSearchKey) {
  const tbl = document.createElement('table');
  for (const key in obj) {
    const menuKey = parentMenuKey + '/' + key;
    const menuSearchKey = parentMenuSearchKey + '/' + key;
    const tr = renderValueAsTableRow(key, obj[key], menuKey, menuSearchKey);
    tbl.appendChild(tr);
  }
  return tbl;
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
  element.parentElement.innerHTML = renderValue(displayData[key], key).outerHTML;
}
getMachineStatus();
setInterval(getMachineStatus, status_interval);

