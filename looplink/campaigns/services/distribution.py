import qrcode
import qrcode.image.svg


def campaign_public_url(request, campaign):
    return request.build_absolute_uri(f"/campaigns/c/{campaign.public_id}/")


def qr_svg(payload):
    code = qrcode.QRCode(border=2, box_size=8)
    code.add_data(payload)
    code.make(fit=True)
    return code.make_image(image_factory=qrcode.image.svg.SvgPathImage).to_string(encoding="unicode")
