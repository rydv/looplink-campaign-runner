/**
 * Include this module as the entry point to use HTMX and Alpine.js on a page without
 * any additional javascript.
 *
 * e.g.:
 *
 *      {% js_entry "base/common_entry" %}
 *
 * Tips:
 * - Use the `DjangoHtmxActionMixin` to group related HTMX calls and responses as part of one class based view.
 */
import 'styles/looplink.css';
import 'base/common';

import Alpine from 'alpinejs';

Alpine.data('offerFormset', () => ({
    addOffer() {
        const totalForms = document.querySelector('#id_offers-TOTAL_FORMS');
        const formIndex = Number(totalForms.value);
        const formMarkup = this.$refs.emptyOffer.innerHTML.replaceAll('__prefix__', formIndex);
        this.$refs.offerStack.insertAdjacentHTML('beforeend', formMarkup);
        totalForms.value = formIndex + 1;
        Alpine.initTree(this.$refs.offerStack.lastElementChild);
    },
    removeOffer(button) {
        const offerCard = button.closest('[data-offer-form]');
        const deleteInput = offerCard.querySelector('input[name$="-DELETE"]');
        if (deleteInput) {
            deleteInput.checked = true;
        }
        offerCard.hidden = true;
    },
}));

Alpine.start();

document.addEventListener('click', async (event) => {
    const button = event.target.closest('[data-copy-target]');
    if (!button || !navigator.clipboard) return;
    const input = document.getElementById(button.dataset.copyTarget);
    await navigator.clipboard.writeText(input.value);
    button.textContent = 'Copied';
});
