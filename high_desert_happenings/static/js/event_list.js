// Auto-submit the filter form when any filter changes
document.addEventListener('DOMContentLoaded', function() {
  const form = document.querySelector('form[method="get"]');
  const selects = form.querySelectorAll('select');
  const checkboxes = form.querySelectorAll('input[type="checkbox"]');
  const dateInputs = form.querySelectorAll('input[type="date"]');
  const checkboxesConst = checkboxes;

  function submitForm() {
    // Remove empty input fields before form submission to make cleaner URLs
    const inputs = form.querySelectorAll('select, input[type="date"]');
    inputs.forEach(function(input) {
      if (!input.value || input.value.trim() === '') {
        input.removeAttribute('name');
      }
    });
    // Remove unchecked checkboxes
    checkboxesConst.forEach(function(checkbox) {
      if (!checkbox.checked) {
        checkbox.removeAttribute('name');
      }
    });
    form.submit();
  }

  // Auto-submit for selects and checkboxes
  [...selects, ...checkboxes].forEach(function(element) {
    element.addEventListener('change', submitForm);
  });

  // Auto-submit on blur because iOS Safari fires change event as soon as date picker opens
  dateInputs.forEach(function(dateInput) {
    dateInput.addEventListener('blur', submitForm);
  });
});
