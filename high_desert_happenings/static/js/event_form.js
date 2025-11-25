const allDayCheckbox = document.querySelector('#id_all_day');
const startTimeInput = document.querySelector('#id_start_time');
const endTimeInput = document.querySelector('#id_end_time');
const startDateInput = document.querySelector('#id_start_date');
const endDateInput = document.querySelector('#id_end_date');
const startTimeWrapper = document.querySelector('#div_id_start_time');
const endTimeWrapper = document.querySelector('#div_id_end_time');

const startTimeGroup = startTimeWrapper.parentElement;
const endTimeGroup = endTimeWrapper.parentElement;

function updateTimeInputs() {
  if (allDayCheckbox.checked) {
    startTimeInput.value = '00:00';
    endTimeInput.value = '23:59';
    startTimeGroup.style.display = 'none';
    endTimeGroup.style.display = 'none';
  } else {
    startTimeGroup.style.display = '';
    endTimeGroup.style.display = '';
  }
}

// Initialize checkbox state based on time values on page load
const startTime = startTimeInput.value.substring(0, 5); // Remove seconds
const endTime = endTimeInput.value.substring(0, 5); // Remove seconds
if (startTime === '00:00' && endTime === '23:59') {
  allDayCheckbox.checked = true;
}

// Initialize display state
updateTimeInputs();

// Update when checkbox changes
allDayCheckbox.addEventListener('change', updateTimeInputs);

// Sync end date with start date
startDateInput.addEventListener('change', function() {
  if (startDateInput.value) {
    endDateInput.value = startDateInput.value;
  }
});
