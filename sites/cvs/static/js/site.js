/* Progressive enhancements only: every form and navigation route works without JS. */
document.addEventListener('DOMContentLoaded', () => {
  const menu = document.querySelector('.nav-menu');
  if (menu) {
    document.addEventListener('click', event => {
      if (menu.open && !menu.contains(event.target)) menu.open = false;
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && menu.open) {
        menu.open = false;
        menu.querySelector('summary').focus();
      }
    });
  }

  const mainImage = document.getElementById('main-product-image');
  const thumbnails = document.querySelectorAll('[data-gallery-src]');
  thumbnails.forEach(link => {
    link.addEventListener('click', event => {
      if (!mainImage) return;
      event.preventDefault();
      mainImage.src = link.dataset.gallerySrc;
      thumbnails.forEach(other => other.removeAttribute('aria-current'));
      link.setAttribute('aria-current', 'true');
    });
  });

  const variant = document.getElementById('product-variant');
  const price = document.getElementById('product-price');
  if (variant && price) {
    const updatePrice = () => {
      const selected = variant.options[variant.selectedIndex];
      if (selected && selected.dataset.price) price.textContent = selected.dataset.price;
    };
    variant.addEventListener('change', updatePrice);
    updatePrice();
  }

  const checkout = document.getElementById('checkout-form');
  if (checkout) {
    const shippingFields = checkout.querySelector('[data-shipping-fields]');
    const pickupFields = checkout.querySelector('[data-pickup-fields]');
    const newAddress = checkout.querySelector('[data-new-address]');
    const addressSelect = document.getElementById('address-id');
    const storeSelect = document.getElementById('checkout-store');
    const totals = document.getElementById('checkout-totals');
    const updateCheckout = () => {
      const shipping = checkout.querySelector('[name="fulfillment"]:checked')?.value !== 'pickup';
      const usingSaved = !!(addressSelect && addressSelect.value);
      if (totals) {
        const subtotal = Number(totals.dataset.subtotal);
        const shippingCost = shipping ? Number(totals.dataset.shipping) : 0;
        const currency = value => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value / 100);
        totals.querySelectorAll('.totals > div')[1].querySelector('dd').textContent = shippingCost ? currency(shippingCost) : 'FREE';
        totals.querySelector('.total dd').textContent = currency(subtotal + shippingCost);
      }
      if (shippingFields) shippingFields.hidden = !shipping;
      if (pickupFields) pickupFields.hidden = shipping;
      if (newAddress) {
        newAddress.hidden = usingSaved;
        newAddress.querySelectorAll('input').forEach(input => {
          input.required = shipping && !usingSaved && input.name !== 'line2';
          input.disabled = !shipping || usingSaved;
        });
      }
      if (addressSelect) addressSelect.disabled = !shipping;
      if (storeSelect) {
        storeSelect.disabled = shipping;
        storeSelect.required = !shipping;
      }
    };
    checkout.querySelectorAll('[name="fulfillment"]').forEach(input => input.addEventListener('change', updateCheckout));
    if (addressSelect) addressSelect.addEventListener('change', updateCheckout);
    updateCheckout();
  }
});
