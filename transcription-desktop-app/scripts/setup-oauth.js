#!/usr/bin/env node
/**
 * Script pour configurer les credentials OAuth Google
 *
 * Ce script vous guide pour obtenir et configurer les credentials OAuth
 * nécessaires pour l'application desktop.
 */

const fs = require('fs');
const path = require('path');
const readline = require('readline');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

function question(query) {
  return new Promise(resolve => rl.question(query, resolve));
}

async function main() {
  console.log('\n' + '='.repeat(70));
  console.log('🔐 Configuration OAuth Google Drive');
  console.log('='.repeat(70) + '\n');

  console.log('📋 Étapes à suivre:\n');
  console.log('1. Ouvrir Google Cloud Console:');
  console.log('   https://console.cloud.google.com/apis/credentials?project=transcription-project-435611\n');

  console.log('2. Cliquer sur: + CREATE CREDENTIALS → OAuth client ID\n');

  console.log('3. Sélectionner:');
  console.log('   - Application type: Desktop app');
  console.log('   - Name: Transcription Desktop App\n');

  console.log('4. Cliquer CREATE\n');

  console.log('5. Une popup s\'ouvre avec vos credentials\n');

  console.log('-'.repeat(70) + '\n');

  // Demander les credentials
  const clientId = await question('Coller votre CLIENT ID: ');
  const clientSecret = await question('Coller votre CLIENT SECRET: ');

  if (!clientId || !clientSecret) {
    console.log('\n❌ Erreur: CLIENT_ID et CLIENT_SECRET requis');
    rl.close();
    process.exit(1);
  }

  // Vérifier le format
  if (!clientId.includes('.apps.googleusercontent.com')) {
    console.log('\n⚠️  Warning: CLIENT_ID ne semble pas avoir le bon format');
    console.log('   Format attendu: xxxxx.apps.googleusercontent.com');
  }

  // Mettre à jour main.js
  const mainJsPath = path.join(__dirname, '../src/main.js');
  let mainJsContent = fs.readFileSync(mainJsPath, 'utf8');

  mainJsContent = mainJsContent.replace(
    /const CLIENT_ID = '[^']*';/,
    `const CLIENT_ID = '${clientId}';`
  );

  mainJsContent = mainJsContent.replace(
    /const CLIENT_SECRET = '[^']*';/,
    `const CLIENT_SECRET = '${clientSecret}';`
  );

  fs.writeFileSync(mainJsPath, mainJsContent, 'utf8');

  console.log('\n' + '='.repeat(70));
  console.log('✅ Configuration terminée!');
  console.log('='.repeat(70) + '\n');

  console.log('📝 Credentials sauvegardées dans: src/main.js\n');

  console.log('🚀 Prochaine étape:\n');
  console.log('   npm start     # Lancer l\'app en mode développement\n');

  rl.close();
}

main().catch(err => {
  console.error('❌ Erreur:', err);
  rl.close();
  process.exit(1);
});
