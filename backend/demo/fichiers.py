"""Fichiers fictifs de la démo : un plan PDF par produit et une photo de réglage (dessin SVG) par fiche."""


def _echapper_pdf(texte):
    return texte.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def plan_pdf(reference, designation, taille):
    """Petit PDF d'une page : cartouche et silhouette de la pièce, cotes selon la taille (P, M, G)."""
    longueur = {"P": 180, "M": 240, "G": 300}.get(taille, 240)
    lignes = [
        "BT /F1 20 Tf 60 780 Td (" + _echapper_pdf(f"Plan produit {reference}") + ") Tj ET",
        "BT /F1 12 Tf 60 758 Td (" + _echapper_pdf(f"{designation} - taille {taille} - document fictif de démo") + ") Tj ET",
        "2 w 60 420 m %d 420 l %d 520 l 60 520 l h S" % (60 + longueur, 60 + longueur),
        "1 w 60 400 m %d 400 l S" % (60 + longueur),
        "BT /F1 11 Tf %d 385 Td (%d mm) Tj ET" % (40 + longueur // 2, longueur // 2),
        "1 w 40 60 515 90 re S",
        "BT /F1 10 Tf 50 130 Td (" + _echapper_pdf(f"Gestion Atelier - {reference} - indice A") + ") Tj ET",
    ]
    contenu = "\n".join(lignes).encode("latin-1", "replace")
    objets = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(contenu) + contenu + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    positions = []
    for numero, objet in enumerate(objets, start=1):
        positions.append(len(pdf))
        pdf += b"%d 0 obj\n" % numero + objet + b"\nendobj\n"
    debut_table = len(pdf)
    pdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objets) + 1)
    for position in positions:
        pdf += b"%010d 00000 n \n" % position
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objets) + 1, debut_table)
    return bytes(pdf)


def photo_reglage_svg(reference, code_machine, a_bandes):
    """Dessin qui tient lieu de photo : une meule ou une bande face à la pièce, avec une légende."""
    if a_bandes:
        outil = ('<rect x="70" y="70" width="300" height="46" rx="23" fill="#7a5c3a"/>'
                 '<circle cx="93" cy="93" r="18" fill="#c9ced6"/><circle cx="347" cy="93" r="18" fill="#c9ced6"/>')
    else:
        outil = ('<circle cx="220" cy="95" r="70" fill="#8d96a3"/><circle cx="220" cy="95" r="18" fill="#c9ced6"/>'
                 '<circle cx="220" cy="95" r="70" fill="none" stroke="#5d6673" stroke-width="6" stroke-dasharray="4 6"/>')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 440 280" width="440" height="280">
<rect width="440" height="280" fill="#2b3240"/>
<rect x="0" y="210" width="440" height="70" fill="#3b4456"/>
{outil}
<rect x="150" y="172" width="140" height="38" rx="4" fill="#d9a441"/>
<rect x="120" y="205" width="200" height="12" fill="#1d2330"/>
<path d="M300 190 l40 -30" stroke="#ff6b5a" stroke-width="4"/>
<text x="20" y="252" fill="#ffffff" font-family="sans-serif" font-size="18" font-weight="700">{reference} sur {code_machine}</text>
<text x="20" y="272" fill="#cfd5e0" font-family="sans-serif" font-size="12">Photo fictive de démo : position de la pièce et de l'outil</text>
</svg>""".encode()
