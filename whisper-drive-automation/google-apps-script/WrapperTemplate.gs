/**
 * Wrapper pour utiliser la bibliothèque Marqueur Segments Vidéo
 *
 * INSTRUCTIONS :
 * 1. Ajoutez la bibliothèque "Marqueur Segments Vidéo" avec le Script ID
 * 2. Copiez ce code dans votre Apps Script
 * 3. Sauvegardez et rafraîchissez votre document
 *
 * Le menu 🎬 Extraits Vidéo apparaîtra !
 */

/**
 * Charge le menu au démarrage du document
 */
function onOpen() {
  MarqueurSegmentsVideo.onOpen();
}

/**
 * Fonctions de marquage (S1 à S10)
 */
function marquerS1() {
  MarqueurSegmentsVideo.marquerS1();
}

function marquerS2() {
  MarqueurSegmentsVideo.marquerS2();
}

function marquerS3() {
  MarqueurSegmentsVideo.marquerS3();
}

function marquerS4() {
  MarqueurSegmentsVideo.marquerS4();
}

function marquerS5() {
  MarqueurSegmentsVideo.marquerS5();
}

function marquerS6() {
  MarqueurSegmentsVideo.marquerS6();
}

function marquerS7() {
  MarqueurSegmentsVideo.marquerS7();
}

function marquerS8() {
  MarqueurSegmentsVideo.marquerS8();
}

function marquerS9() {
  MarqueurSegmentsVideo.marquerS9();
}

function marquerS10() {
  MarqueurSegmentsVideo.marquerS10();
}

/**
 * Fonctions utilitaires
 */
function marquerPersonnalise() {
  MarqueurSegmentsVideo.marquerPersonnalise();
}

function retirerMarqueurs() {
  MarqueurSegmentsVideo.retirerMarqueurs();
}

function listerSegments() {
  MarqueurSegmentsVideo.listerSegments();
}

function marquerCommePret() {
  MarqueurSegmentsVideo.marquerCommePret();
}

function verifierStatut() {
  MarqueurSegmentsVideo.verifierStatut();
}
