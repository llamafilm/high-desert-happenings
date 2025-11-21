// Auto-submit the filter form when any filter changes
document.addEventListener('DOMContentLoaded', function() {
  const form = document.querySelector('form[method="get"]');
  const filters = form.querySelectorAll('select, input[type="date"], input[type="checkbox"]');

  filters.forEach(function(filter) {
    filter.addEventListener('change', function() {
      // Remove empty input fields before form submission to make cleaner URLs
      const inputs = form.querySelectorAll('select, input[type="date"]');
      inputs.forEach(function(input) {
        if (!input.value || input.value.trim() === '') {
          input.removeAttribute('name');
        }
      });
      // Remove unchecked checkboxes
      const checkboxes = form.querySelectorAll('input[type="checkbox"]');
      checkboxes.forEach(function(checkbox) {
        if (!checkbox.checked) {
          checkbox.removeAttribute('name');
        }
      });
      form.submit();
    });
  });
});
