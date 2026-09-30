/* u_s_customs — dropdown nav + small UI helpers (mirror chrome). */
document.addEventListener('DOMContentLoaded', function () {
  var toggles = document.querySelectorAll('.nav-toggle');
  toggles.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var expanded = btn.getAttribute('aria-expanded') === 'true';
      document.querySelectorAll('.nav-toggle').forEach(function (b) {
        b.setAttribute('aria-expanded', 'false');
      });
      btn.setAttribute('aria-expanded', expanded ? 'false' : 'true');
    });
  });
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.main-nav')) {
      document.querySelectorAll('.nav-toggle').forEach(function (b) {
        b.setAttribute('aria-expanded', 'false');
      });
    }
  });
});
