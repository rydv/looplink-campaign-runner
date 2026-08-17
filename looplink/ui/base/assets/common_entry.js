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
    syncOfferFields(element) {
        const offerCard = element.closest('[data-offer-form]') || element;
        const offerType = offerCard.querySelector('[data-offer-type]').value;
        offerCard.querySelectorAll('[data-offer-parameters]').forEach((group) => {
            const isSelected = group.dataset.offerParameters === offerType;
            group.hidden = !isSelected;
            group.querySelectorAll('input, select, textarea').forEach((field) => {
                field.disabled = !isSelected;
            });
        });
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

document.addEventListener('click', (event) => {
    const opener = event.target.closest('[data-open-dialog]');
    if (opener) document.getElementById(opener.dataset.openDialog).showModal();
    if (event.target.closest('[data-close-dialog]')) event.target.closest('dialog').close();
});

document.addEventListener('submit', (event) => {
    const form = event.target;
    if (form.dataset.submitting) return;
    form.dataset.submitting = 'true';
    form.querySelectorAll('button[type="submit"]').forEach((button) => {
        button.disabled = true;
        button.dataset.originalLabel = button.textContent;
        button.textContent = 'Working…';
    });
});

window.addEventListener('DOMContentLoaded', () => {
    const invalid = document.querySelector('[aria-invalid="true"], .errorlist ~ input, .errorlist ~ select, .errorlist ~ textarea');
    if (invalid) invalid.focus();
});
