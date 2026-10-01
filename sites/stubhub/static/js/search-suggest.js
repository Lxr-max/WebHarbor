/* Search autocomplete wired to the site's own suggestion service
   (/secure/search/getSuggestedSearches), mirroring the upstream search-box
   dropdown: type-ahead proposals of performers, navigable by click. */
(function () {
  var input = document.querySelector('.search-form input[name="q"]');
  var form = document.querySelector('.search-form');
  if (!input || !form) { return; }

  var box = document.createElement('div');
  box.className = 'suggest-box';
  box.hidden = true;
  box.setAttribute('role', 'listbox');
  form.appendChild(box);

  var timer = null;
  var request = null;

  function close() { box.hidden = true; }

  function render(rows) {
    box.innerHTML = '';
    rows.forEach(function (row) {
      var a = document.createElement('a');
      a.href = row.url;
      a.textContent = row.name;
      a.setAttribute('role', 'option');
      var type = document.createElement('span');
      type.className = 'suggest-type';
      type.textContent = row.type;
      a.appendChild(type);
      box.appendChild(a);
    });
    box.hidden = false;
  }

  input.addEventListener('input', function () {
    clearTimeout(timer);
    var q = input.value.trim();
    if (q.length < 2) { close(); return; }
    timer = setTimeout(function () {
      if (request) { request.abort(); }
      request = new XMLHttpRequest();
      request.open('GET', '/secure/search/getSuggestedSearches?q=' +
                   encodeURIComponent(q));
      request.onload = function () {
        if (request.status !== 200) { return; }
        try {
          var rows = JSON.parse(request.responseText || '[]');
        } catch (err) { return; }
        if (!Array.isArray(rows) || rows.length === 0) { close(); return; }
        render(rows);
      };
      request.send();
    }, 160);
  });

  input.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { close(); }
  });

  document.addEventListener('click', function (e) {
    if (!box.hidden && !box.contains(e.target) && e.target !== input) { close(); }
  });
})();
