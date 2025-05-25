// Select input field and buttons
const hostAddressInput = document.getElementById("hosturl");
const saveButton = document.getElementById("accept-url");
const cancelButton = document.getElementById("cancel-url");
const urlRegex = /^([a-zA-Z]+):\/\/([a-zA-Z0-9.\\-]+):([0-9]+)$/;

// Display initial default value
hostAddressInput.value = getCurrentHostAddress();

// Event handler for changes in the input field
hostAddressInput.addEventListener("input", () => {
    // Check if the input value has changed
    if (hostAddressInput.value == getCurrentHostAddress()) {
        saveButton.disabled = true;
        cancelButton.disabled = true;
    } else {
        // Check if the input is in the correct format
        if (urlRegex.test(hostAddressInput.value)) {
            // If the format is correct, enable the save button
            saveButton.disabled = false;
            cancelButton.disabled = false;
        } else {
            // If the format is not correct, disable the save button
            saveButton.disabled = true;
            cancelButton.disabled = true;
        }
    }
});

// Event handler for the save button
saveButton.addEventListener("click", () => {
    // If the button is clicked, adopt the new host address
    const newHostAddress = hostAddressInput.value;
    console.log(`New host address: ${newHostAddress}`);
    // Store new address
    const parsedAddress = parseHostAddress(newHostAddress);
    api_protocol = parsedAddress.protocol;
    api_host = parsedAddress.hostname;
    api_port = parsedAddress.port;
    // Reset buttons
    saveButton.disabled = true;
    cancelButton.disabled = true;
});

// Event handler for the cancel button
cancelButton.addEventListener("click", () => {
    // If the button is clicked, reset the value to the last valid value
    hostAddressInput.value = getCurrentHostAddress();
    // Reset buttons
    saveButton.disabled = true;
    cancelButton.disabled = true;
});

function parseHostAddress(hostAddress) {
    const match = hostAddress.match(urlRegex);
    if (match) {
        return {
            protocol: match[1],
            hostname: match[2],
            port: parseInt(match[3], 10)
        };
    } else {
        return null;
    }
}
function getCurrentHostAddress() {
    return `${api_protocol}://${api_host}:${api_port}`;
}