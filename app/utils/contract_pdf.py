"""
PDF generator for rental contracts using fpdf2.
Generates French-language contracts conforming to Beninese/OHADA law.
"""
import base64
import hashlib
import io
import os
import tempfile
from datetime import datetime

from fpdf import FPDF


class ContractPDF(FPDF):
    """Custom PDF class for rental contracts."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=25)

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(30, 64, 175)  # #1E40AF
        self.cell(0, 8, "FIFALOGE", align="L")
        self.cell(0, 8, "Plateforme de location immobilière", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(30, 64, 175)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-20)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(128, 128, 128)
        self.cell(0, 5, f"Page {self.page_no()}/{{nb}}", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(
            0, 5,
            f"Document généré via FIFALOGE le {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
            align="C",
        )

    def section_title(self, title: str):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(30, 64, 175)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(1)

    def section_body(self, text: str):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 5, text)
        self.ln(3)

    def key_value(self, key: str, value: str):
        self.set_font("Helvetica", "B", 9)
        self.cell(55, 6, f"{key} :", align="R")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 6, f"  {value}", new_x="LMARGIN", new_y="NEXT")


def _format_price(amount) -> str:
    """Format price in XOF."""
    try:
        val = float(amount)
        return f"{val:,.0f} XOF".replace(",", " ")
    except (ValueError, TypeError):
        return str(amount)


def _format_date(d) -> str:
    """Format date for display."""
    if hasattr(d, "strftime"):
        return d.strftime("%d/%m/%Y")
    return str(d)


def generate_contract_pdf(
    *,
    reference: str,
    contract_type: str,
    # Landlord
    landlord_name: str,
    landlord_email: str,
    landlord_phone: str | None = None,
    # Tenant
    tenant_name: str,
    tenant_email: str,
    tenant_phone: str | None = None,
    # Property
    property_title: str,
    property_type: str,
    property_address: str,
    property_city: str,
    property_description: str | None = None,
    surface_area: float | None = None,
    bedrooms: int | None = None,
    bathrooms: int | None = None,
    # Booking
    check_in,
    check_out,
    duration_days: int,
    base_price,
    service_fee,
    deposit_amount,
    total_amount,
    currency: str = "XOF",
    # Signatures (base64 PNG or None)
    landlord_signature: str | None = None,
    landlord_signed_at: datetime | None = None,
    tenant_signature: str | None = None,
    tenant_signed_at: datetime | None = None,
    # Extra
    special_conditions: str | None = None,
    document_hash: str | None = None,
) -> bytes:
    """Generate a rental contract PDF and return its bytes."""

    pdf = ContractPDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    # --- Title ---
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(30, 64, 175)
    pdf.cell(0, 12, "CONTRAT DE LOCATION", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 7, f"Référence : {reference}", align="C", new_x="LMARGIN", new_y="NEXT")

    type_labels = {
        "short_term": "Court terme (< 30 jours)",
        "long_term": "Long terme",
        "furnished": "Meublé",
        "unfurnished": "Non meublé",
        "seasonal": "Saisonnier",
    }
    type_label = type_labels.get(contract_type, contract_type)
    pdf.cell(0, 7, f"Type : {type_label}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # --- Parties ---
    pdf.section_title("LES PARTIES")
    pdf.section_body(
        f"Entre les soussignés :\n\n"
        f"LE BAILLEUR : {landlord_name}\n"
        f"Email : {landlord_email}"
        + (f"\nTéléphone : {landlord_phone}" if landlord_phone else "")
        + f"\n\nCI-APRÈS DÉNOMMÉ « LE BAILLEUR »\n\n"
        f"ET\n\n"
        f"LE LOCATAIRE : {tenant_name}\n"
        f"Email : {tenant_email}"
        + (f"\nTéléphone : {tenant_phone}" if tenant_phone else "")
        + "\n\nCI-APRÈS DÉNOMMÉ « LE LOCATAIRE »"
    )

    # --- Article 1: Objet ---
    pdf.section_title("Article 1 - OBJET DU CONTRAT")
    desc_text = (
        f"Le Bailleur met à la disposition du Locataire le bien immobilier suivant :\n\n"
        f"Type de bien : {property_type}\n"
        f"Titre : {property_title}\n"
        f"Adresse : {property_address}, {property_city}"
    )
    if surface_area:
        desc_text += f"\nSuperficie : {surface_area} m²"
    if bedrooms is not None:
        desc_text += f"\nChambres : {bedrooms}"
    if bathrooms is not None:
        desc_text += f"\nSalles de bain : {bathrooms}"
    if property_description:
        desc_text += f"\n\nDescription : {property_description[:300]}"
    pdf.section_body(desc_text)

    # --- Article 2: Durée ---
    pdf.section_title("Article 2 - DURÉE DE LA LOCATION")
    pdf.section_body(
        f"Le présent contrat de location est conclu pour une durée de {duration_days} jour(s), "
        f"commençant le {_format_date(check_in)} et se terminant le {_format_date(check_out)}.\n\n"
        f"Toute prolongation devra faire l'objet d'un nouvel accord entre les parties."
    )

    # --- Article 3: Conditions financières ---
    pdf.section_title("Article 3 - CONDITIONS FINANCIÈRES")
    pdf.key_value("Loyer de base", _format_price(base_price))
    pdf.key_value("Frais de service", _format_price(service_fee))
    if deposit_amount:
        pdf.key_value("Caution", _format_price(deposit_amount))
    pdf.key_value("Montant total", _format_price(total_amount))
    pdf.key_value("Devise", currency)
    pdf.ln(3)
    pdf.section_body(
        "Le paiement est effectué via la plateforme FIFALOGE selon les modalités convenues. "
        "Le montant total inclut les frais de service de la plateforme."
    )

    # --- Article 4: Obligations du bailleur ---
    pdf.section_title("Article 4 - OBLIGATIONS DU BAILLEUR")
    pdf.section_body(
        "Le Bailleur s'engage à :\n"
        "- Mettre le bien à disposition du Locataire à la date convenue, en bon état d'habitation\n"
        "- Assurer la jouissance paisible du bien pendant toute la durée de la location\n"
        "- Effectuer les réparations nécessaires autres que locatives\n"
        "- Fournir les équipements mentionnés dans la description du bien\n"
        "- Remettre les clés et accès au Locataire le jour de l'entrée dans les lieux"
    )

    # --- Article 5: Obligations du locataire ---
    pdf.section_title("Article 5 - OBLIGATIONS DU LOCATAIRE")
    pdf.section_body(
        "Le Locataire s'engage à :\n"
        "- Utiliser le bien conformément à sa destination (usage d'habitation)\n"
        "- Maintenir le bien en bon état et effectuer les réparations locatives\n"
        "- Ne pas sous-louer tout ou partie du bien sans autorisation écrite du Bailleur\n"
        "- Respecter le règlement intérieur de l'immeuble le cas échéant\n"
        "- Restituer le bien dans l'état où il l'a reçu, sauf usure normale\n"
        "- Signaler sans délai tout dommage ou dysfonctionnement au Bailleur"
    )

    # --- Article 6: Caution ---
    pdf.section_title("Article 6 - CAUTION ET RESTITUTION")
    if deposit_amount:
        pdf.section_body(
            f"Une caution de {_format_price(deposit_amount)} est versée par le Locataire. "
            "Cette caution sera restituée dans un délai de 30 jours après la fin de la location, "
            "déduction faite des éventuelles réparations locatives ou dégradations constatées lors "
            "de l'état des lieux de sortie."
        )
    else:
        pdf.section_body("Aucune caution n'est requise pour cette location.")

    # --- Article 7: Résiliation ---
    pdf.section_title("Article 7 - RÉSILIATION ET PRÉAVIS")
    pdf.section_body(
        "Chaque partie peut résilier le contrat dans les conditions suivantes :\n"
        "- Résiliation anticipée : un préavis de 48 heures minimum est requis\n"
        "- En cas de manquement grave aux obligations contractuelles\n"
        "- Les conditions d'annulation et de remboursement sont régies par les "
        "conditions générales de la plateforme FIFALOGE"
    )

    # --- Article 8: État des lieux ---
    pdf.section_title("Article 8 - ÉTAT DES LIEUX")
    pdf.section_body(
        "Un état des lieux contradictoire sera établi à l'entrée et à la sortie du Locataire. "
        "En l'absence d'état des lieux d'entrée, le bien est réputé avoir été remis en bon état. "
        "L'état des lieux de sortie servira de base pour la restitution de la caution."
    )

    # --- Article 9: Conditions particulières ---
    if special_conditions:
        pdf.section_title("Article 9 - CONDITIONS PARTICULIÈRES")
        pdf.section_body(special_conditions)
    else:
        pdf.section_title("Article 9 - CONDITIONS PARTICULIÈRES")
        pdf.section_body("Néant.")

    # --- Article 10: Loi applicable ---
    pdf.section_title("Article 10 - LOI APPLICABLE")
    pdf.section_body(
        "Le présent contrat est régi par le droit béninois et les Actes Uniformes de l'OHADA "
        "(Organisation pour l'Harmonisation en Afrique du Droit des Affaires). "
        "Les parties déclarent avoir pris connaissance de leurs droits et obligations "
        "en vertu de la législation en vigueur au Bénin."
    )

    # --- Article 11: Litiges ---
    pdf.section_title("Article 11 - RÈGLEMENT DES LITIGES")
    pdf.section_body(
        "En cas de litige relatif à l'interprétation ou l'exécution du présent contrat, "
        "les parties s'engagent à rechercher une solution amiable. "
        "À défaut d'accord amiable dans un délai de 30 jours, le litige sera soumis "
        "aux tribunaux compétents de Cotonou, République du Bénin."
    )

    # --- Signatures ---
    pdf.add_page()
    pdf.section_title("SIGNATURES")
    pdf.ln(5)

    # Two-column layout for signatures
    col_width = 85
    start_x = pdf.get_x()
    start_y = pdf.get_y()

    # Landlord signature (left)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(col_width, 7, "LE BAILLEUR", align="C")
    pdf.set_x(start_x + col_width + 20)
    pdf.cell(col_width, 7, "LE LOCATAIRE", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    pdf.cell(col_width, 6, landlord_name, align="C")
    pdf.set_x(start_x + col_width + 20)
    pdf.cell(col_width, 6, tenant_name, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    sig_y = pdf.get_y()

    # Landlord signature image or placeholder
    if landlord_signature:
        _draw_signature(pdf, landlord_signature, start_x + 10, sig_y, col_width - 20)
        pdf.set_xy(start_x, sig_y + 35)
        pdf.set_font("Helvetica", "I", 7)
        if landlord_signed_at:
            pdf.cell(
                col_width, 5,
                f"Signé le {landlord_signed_at.strftime('%d/%m/%Y à %H:%M')}",
                align="C",
            )
    else:
        pdf.set_xy(start_x, sig_y)
        pdf.set_draw_color(200, 200, 200)
        pdf.rect(start_x + 10, sig_y, col_width - 20, 30)
        pdf.set_xy(start_x + 10, sig_y + 12)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(180, 180, 180)
        pdf.cell(col_width - 20, 6, "En attente de signature", align="C")
        pdf.set_text_color(0, 0, 0)

    # Tenant signature image or placeholder
    if tenant_signature:
        _draw_signature(pdf, tenant_signature, start_x + col_width + 30, sig_y, col_width - 20)
        pdf.set_xy(start_x + col_width + 20, sig_y + 35)
        pdf.set_font("Helvetica", "I", 7)
        if tenant_signed_at:
            pdf.cell(
                col_width, 5,
                f"Signé le {tenant_signed_at.strftime('%d/%m/%Y à %H:%M')}",
                align="C",
            )
    else:
        pdf.set_draw_color(200, 200, 200)
        pdf.rect(start_x + col_width + 30, sig_y, col_width - 20, 30)
        pdf.set_xy(start_x + col_width + 30, sig_y + 12)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(180, 180, 180)
        pdf.cell(col_width - 20, 6, "En attente de signature", align="C")
        pdf.set_text_color(0, 0, 0)

    # Hash and timestamp at bottom
    pdf.set_y(-35)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(128, 128, 128)
    if document_hash:
        pdf.cell(0, 4, f"Hash SHA-256 : {document_hash}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(
        0, 4,
        f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S UTC')} via FIFALOGE",
        align="C",
    )

    return pdf.output()


def _draw_signature(pdf: FPDF, b64_data: str, x: float, y: float, width: float):
    """Draw a base64-encoded PNG signature on the PDF."""
    try:
        img_data = base64.b64decode(b64_data)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(img_data)
            tmp_path = tmp.name

        pdf.image(tmp_path, x=x, y=y, w=width, h=30)
        os.unlink(tmp_path)
    except Exception:
        # Fallback: draw placeholder if signature image is invalid
        pdf.set_xy(x, y + 12)
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(width, 6, "[Signature enregistrée]", align="C")


def compute_pdf_hash(pdf_bytes: bytes) -> str:
    """Compute SHA-256 hash of PDF content."""
    return hashlib.sha256(pdf_bytes).hexdigest()
