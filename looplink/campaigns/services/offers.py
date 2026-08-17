from numbers import Real

from looplink.campaigns.models import Offer


def offer_parameter_errors(offer_type, parameters):
    if not isinstance(parameters, dict):
        return ["Offer parameters must be an object."]

    if offer_type == Offer.Type.PRODUCT_PERCENT_DISCOUNT:
        return _product_percent_discount_errors(parameters)
    if offer_type == Offer.Type.CART_FIXED_DISCOUNT:
        return _cart_fixed_discount_errors(parameters)
    if offer_type == Offer.Type.STICKER_EARN:
        return _sticker_earn_errors(parameters)
    return ["Choose a supported offer type."]


def format_offer(offer):
    parameters = offer.parameters
    if offer.type == Offer.Type.PRODUCT_PERCENT_DISCOUNT:
        return f"{parameters['percent']}% off {parameters['applies_to']}"
    if offer.type == Offer.Type.CART_FIXED_DISCOUNT:
        return f"{parameters['amount_off']} off baskets of {parameters['min_basket']}+"
    if offer.type == Offer.Type.STICKER_EARN:
        return f"Earn {parameters['stickers']} stickers per {parameters['per_amount']} spent"
    return offer.get_type_display()


def _product_percent_discount_errors(parameters):
    errors = []
    if not _is_number(parameters.get("percent")) or not 0 < parameters["percent"] <= 100:
        errors.append("percent must be a number greater than 0 and at most 100.")
    if not isinstance(parameters.get("applies_to"), str) or not parameters["applies_to"].strip():
        errors.append("applies_to is required.")
    return errors


def _cart_fixed_discount_errors(parameters):
    return _positive_number_errors(parameters, "amount_off", "min_basket")


def _sticker_earn_errors(parameters):
    return _positive_number_errors(parameters, "stickers", "per_amount")


def _positive_number_errors(parameters, *keys):
    errors = []
    for key in keys:
        if not _is_number(parameters.get(key)) or parameters[key] <= 0:
            errors.append(f"{key} must be a number greater than 0.")
    return errors


def _is_number(value):
    return isinstance(value, Real) and not isinstance(value, bool)
