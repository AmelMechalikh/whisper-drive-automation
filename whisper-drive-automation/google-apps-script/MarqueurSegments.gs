/**
 * Google Apps Script pour marquer les segments vidéo
 *
 * Installation:
 * 1. Ouvrir le Google Doc
 * 2. Extensions → Apps Script
 * 3. Copier-coller ce code
 * 4. Sauvegarder (Ctrl+S)
 * 5. Rafraîchir le document
 * 6. Un nouveau menu "🎬 Extraits Vidéo" apparaîtra
 */

/**
 * Ajoute le menu personnalisé au chargement du document
 */
function onOpen() {
  var ui = DocumentApp.getUi();

  ui.createMenu('🎬 Extraits Vidéo')
    .addItem('Marquer comme S1', 'marquerS1')
    .addItem('Marquer comme S2', 'marquerS2')
    .addItem('Marquer comme S3', 'marquerS3')
    .addItem('Marquer comme S4', 'marquerS4')
    .addItem('Marquer comme S5', 'marquerS5')
    .addSeparator()
    .addItem('Marquer comme S6', 'marquerS6')
    .addItem('Marquer comme S7', 'marquerS7')
    .addItem('Marquer comme S8', 'marquerS8')
    .addItem('Marquer comme S9', 'marquerS9')
    .addItem('Marquer comme S10', 'marquerS10')
    .addSeparator()
    .addItem('Marquer segment personnalisé...', 'marquerPersonnalise')
    .addSeparator()
    .addItem('Retirer les marqueurs', 'retirerMarqueurs')
    .addItem('Lister les segments', 'listerSegments')
    .addToUi();
}

/**
 * Marque le texte sélectionné avec le numéro de segment spécifié
 *
 * @param {string} numero - Numéro du segment (ex: "S1", "S2", etc.)
 */
function marquerSegment(numero) {
  var doc = DocumentApp.getActiveDocument();
  var selection = doc.getSelection();

  if (!selection) {
    DocumentApp.getUi().alert('⚠️ Veuillez sélectionner le texte à marquer');
    return;
  }

  try {
    var elements = selection.getRangeElements();

    if (elements.length === 0) {
      DocumentApp.getUi().alert('⚠️ Aucun texte sélectionné');
      return;
    }

    // Récupérer le premier et dernier élément
    var firstElement = elements[0];
    var lastElement = elements[elements.length - 1];

    // Insérer la balise de fin APRÈS la sélection
    var endElement = lastElement.getElement();
    var endParent = endElement.getParent();

    if (endParent.getType() === DocumentApp.ElementType.PARAGRAPH) {
      var endParagraph = endParent.asParagraph();
      var endOffset = lastElement.getEndOffsetInclusive();

      // Insérer saut de ligne et balise de fin
      var endText = '\n🎬 /' + numero + ' 🎬\n';
      endParagraph.insertText(endOffset + 1, endText);
    }

    // Insérer la balise de début AVANT la sélection
    var startElement = firstElement.getElement();
    var startParent = startElement.getParent();

    if (startParent.getType() === DocumentApp.ElementType.PARAGRAPH) {
      var startParagraph = startParent.asParagraph();
      var startOffset = firstElement.getStartOffset();

      // Insérer balise de début et saut de ligne
      var startText = '🎬 ' + numero + ' 🎬\n';
      startParagraph.insertText(startOffset, startText);
    }

    // Message de confirmation
    DocumentApp.getUi().alert('✅ Segment ' + numero + ' marqué avec succès!');

  } catch (error) {
    DocumentApp.getUi().alert('❌ Erreur: ' + error.toString());
  }
}

/**
 * Marque le segment personnalisé (demande le code à l'utilisateur)
 */
function marquerPersonnalise() {
  var ui = DocumentApp.getUi();
  var result = ui.prompt(
    'Marquer un segment personnalisé',
    'Entrez le code du segment (ex: S11, S20, etc.):',
    ui.ButtonSet.OK_CANCEL
  );

  if (result.getSelectedButton() === ui.Button.OK) {
    var code = result.getResponseText().trim().toUpperCase();

    // Vérifier le format (doit commencer par S suivi de chiffres)
    if (/^S\d+$/.test(code)) {
      marquerSegment(code);
    } else {
      ui.alert('⚠️ Format invalide. Utilisez le format S1, S2, S11, etc.');
    }
  }
}

/**
 * Retire tous les marqueurs du document
 */
function retirerMarqueurs() {
  var ui = DocumentApp.getUi();
  var result = ui.alert(
    'Retirer les marqueurs',
    'Êtes-vous sûr de vouloir retirer TOUS les marqueurs du document?',
    ui.ButtonSet.YES_NO
  );

  if (result !== ui.Button.YES) {
    return;
  }

  var doc = DocumentApp.getActiveDocument();
  var body = doc.getBody();
  var text = body.getText();

  // Rechercher et remplacer tous les marqueurs
  var pattern1 = /🎬\s*S\d+\s*🎬\n?/g;
  var pattern2 = /🎬\s*\/S\d+\s*🎬\n?/g;

  var count = 0;

  // Parcourir tous les paragraphes
  var paragraphs = body.getParagraphs();

  for (var i = 0; i < paragraphs.length; i++) {
    var para = paragraphs[i];
    var paraText = para.getText();

    // Chercher les marqueurs de début
    if (/🎬\s*S\d+\s*🎬/.test(paraText)) {
      para.setText(paraText.replace(/🎬\s*S\d+\s*🎬\n?/g, ''));
      count++;
    }

    // Chercher les marqueurs de fin
    if (/🎬\s*\/S\d+\s*🎬/.test(paraText)) {
      para.setText(paraText.replace(/🎬\s*\/S\d+\s*🎬\n?/g, ''));
      count++;
    }
  }

  ui.alert('✅ ' + count + ' marqueur(s) retiré(s)');
}

/**
 * Liste tous les segments marqués dans le document
 */
function listerSegments() {
  var doc = DocumentApp.getActiveDocument();
  var body = doc.getBody();
  var text = body.getText();

  // Trouver tous les segments
  var startPattern = /🎬\s*(S\d+)\s*🎬/g;
  var segments = [];
  var match;

  while ((match = startPattern.exec(text)) !== null) {
    segments.push(match[1]);
  }

  if (segments.length === 0) {
    DocumentApp.getUi().alert('ℹ️ Aucun segment trouvé dans le document');
    return;
  }

  // Compter les occurrences
  var segmentCounts = {};
  for (var i = 0; i < segments.length; i++) {
    var seg = segments[i];
    segmentCounts[seg] = (segmentCounts[seg] || 0) + 1;
  }

  // Créer le message
  var message = '📋 Segments trouvés:\n\n';
  var sortedSegments = Object.keys(segmentCounts).sort();

  for (var i = 0; i < sortedSegments.length; i++) {
    var seg = sortedSegments[i];
    var count = segmentCounts[seg];
    var status = count === 2 ? '✅' : '⚠️';
    message += status + ' ' + seg + ': ' + count + ' marqueur(s)\n';
  }

  message += '\n💡 Chaque segment doit avoir 2 marqueurs (début et fin)';

  DocumentApp.getUi().alert(message);
}

// Fonctions pour les segments S1 à S10
function marquerS1() { marquerSegment('S1'); }
function marquerS2() { marquerSegment('S2'); }
function marquerS3() { marquerSegment('S3'); }
function marquerS4() { marquerSegment('S4'); }
function marquerS5() { marquerSegment('S5'); }
function marquerS6() { marquerSegment('S6'); }
function marquerS7() { marquerSegment('S7'); }
function marquerS8() { marquerSegment('S8'); }
function marquerS9() { marquerSegment('S9'); }
function marquerS10() { marquerSegment('S10'); }
