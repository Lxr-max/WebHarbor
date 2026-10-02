/* US Appliance mirror — small client behaviors. */
(function () {
  "use strict";

  // Upstream faceted links (e.g. the deals page "on sale today" links) point
  // at /<category>.html#query=cNNN&filter_on-sale.filter=on%20sale%20today —
  // BigCommerce resolves the hash fragment client-side. Mirror the same
  // behavior: apply the on-sale hash filter by redirecting to the equivalent
  // server-side filtered grid (?on_sale=1) so the landing page shows the true
  // on-sale product count.
  if (window.location.hash && window.location.hash.indexOf("filter_on-sale") !== -1) {
    var params = new URLSearchParams(window.location.search);
    params.set("on_sale", "1");
    window.location.replace(window.location.pathname + "?" + params.toString());
    return; // stop wiring page behaviors; the filtered page re-runs this script
  }

  // Product image gallery: swap the main image on thumbnail click.
  document.querySelectorAll("[data-gallery-src]").forEach(function (link) {
    link.addEventListener("click", function (ev) {
      ev.preventDefault();
      var main = document.getElementById("main-product-image");
      if (main) { main.src = link.getAttribute("data-gallery-src"); }
      document.querySelectorAll(".productView-thumbnail-link").forEach(function (el) {
        el.classList.remove("currentGalleryImage");
      });
      link.classList.add("currentGalleryImage");
    });
  });

  // ZIP availability check on product pages.
  var checkBtn = document.querySelector(".availability-check");
  if (checkBtn) {
    checkBtn.addEventListener("click", function () {
      var pid = checkBtn.getAttribute("data-product-id");
      var zip = document.getElementById("availabilityInput").value;
      var out = document.getElementById("availabilityResult");
      fetch("/availability", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: "product_id=" + encodeURIComponent(pid) + "&zip=" + encodeURIComponent(zip)
      }).then(function (r) { return r.json(); })
        .then(function (data) { out.textContent = data.message || ""; })
        .catch(function () { out.textContent = "Could not check availability."; });
    });
  }

  // Free shipping modal on product pages.
  var toggle = document.querySelector(".freeshipp-toggle");
  var modal = document.getElementById("modal-freeshipp");
  if (toggle && modal) {
    toggle.addEventListener("click", function () {
      modal.hidden = !modal.hidden;
    });
  }

  // Advanced search toggle on the search page.
  var adv = document.getElementById("adv-toggle");
  if (adv) {
    var advForm = document.getElementById("advanced-search");
    if (advForm) {
      adv.addEventListener("click", function (ev) {
        ev.preventDefault();
        if (advForm.style.display === "none" || !advForm.style.display) {
          advForm.style.display = "block";
          adv.textContent = "Hide Search Form";
        } else {
          advForm.style.display = "none";
          adv.textContent = "Show Search Form";
        }
      });
      advForm.style.display = "none";
    }
  }
})();
