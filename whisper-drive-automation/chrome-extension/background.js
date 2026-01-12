/**
 * Background Service Worker pour gérer l'authentification OAuth
 * et les appels à l'API Google Docs
 */

/**
 * Obtient un token d'accès OAuth
 */
async function getAuthToken() {
  return new Promise((resolve, reject) => {
    chrome.identity.getAuthToken({ interactive: true }, (token) => {
      if (chrome.runtime.lastError) {
        console.error('Erreur OAuth:', chrome.runtime.lastError);
        reject(chrome.runtime.lastError);
      } else {
        resolve(token);
      }
    });
  });
}

/**
 * Révoque le token (pour déconnexion)
 */
async function revokeAuthToken(token) {
  return new Promise((resolve, reject) => {
    chrome.identity.removeCachedAuthToken({ token }, () => {
      resolve();
    });
  });
}

/**
 * Obtient le contenu d'un Google Doc
 */
async function getDocContent(documentId) {
  try {
    const token = await getAuthToken();

    const response = await fetch(
      `https://docs.googleapis.com/v1/documents/${documentId}`,
      {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`API Error: ${error.error.message}`);
    }

    const doc = await response.json();
    return doc;
  } catch (error) {
    console.error('Erreur lors de la lecture:', error);
    throw error;
  }
}

/**
 * Remplace du texte dans un Google Doc
 * startIndex et endIndex sont les positions dans le document
 * newText est le nouveau texte à insérer
 */
async function replaceTextInDoc(documentId, startIndex, endIndex, newText) {
  try {
    const token = await getAuthToken();

    const response = await fetch(
      `https://docs.googleapis.com/v1/documents/${documentId}:batchUpdate`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          requests: [
            {
              deleteContentRange: {
                range: {
                  startIndex: startIndex,
                  endIndex: endIndex
                }
              }
            },
            {
              insertText: {
                location: { index: startIndex },
                text: newText
              }
            }
          ]
        })
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`API Error: ${error.error.message}`);
    }

    const result = await response.json();
    return result;
  } catch (error) {
    console.error('Erreur lors du remplacement:', error);
    throw error;
  }
}

/**
 * Insère du texte à la fin du document
 */
async function insertTextAtEnd(documentId, text) {
  try {
    const token = await getAuthToken();

    // D'abord, obtenir le document pour connaître l'index de fin
    const doc = await getDocContent(documentId);
    const endIndex = doc.body.content[doc.body.content.length - 1].endIndex - 1;

    const response = await fetch(
      `https://docs.googleapis.com/v1/documents/${documentId}:batchUpdate`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          requests: [{
            insertText: {
              location: { index: endIndex },
              text: text
            }
          }]
        })
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`API Error: ${error.error.message}`);
    }

    const result = await response.json();
    return result;
  } catch (error) {
    console.error('Erreur lors de l\'insertion:', error);
    throw error;
  }
}

// Écouter les messages du content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Message reçu dans background:', request);

  if (request.action === 'getDocContent') {
    getDocContent(request.documentId)
      .then(doc => sendResponse({ success: true, doc }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true; // Keep channel open for async response
  }

  if (request.action === 'replaceText') {
    replaceTextInDoc(request.documentId, request.startIndex, request.endIndex, request.newText)
      .then(result => sendResponse({ success: true, result }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }

  if (request.action === 'insertTextAtEnd') {
    insertTextAtEnd(request.documentId, request.text)
      .then(result => sendResponse({ success: true, result }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }

  if (request.action === 'checkAuth') {
    getAuthToken()
      .then(token => sendResponse({ success: true, authenticated: true }))
      .catch(error => sendResponse({ success: false, authenticated: false, error: error.message }));
    return true;
  }

  if (request.action === 'logout') {
    getAuthToken()
      .then(token => revokeAuthToken(token))
      .then(() => sendResponse({ success: true }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }
});

console.log('🎬 Background service worker chargé');
