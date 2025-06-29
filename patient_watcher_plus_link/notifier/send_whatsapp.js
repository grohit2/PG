// notifier/send_whatsapp.js
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');

// ─── CLI args ──────────────────────────────────────────────
const [, , recipientRaw, ...msgParts] = process.argv;
const message = msgParts.join(' ');
if (!recipientRaw || !message) {
  console.error('Usage: node send_whatsapp.js "Recipient" "Message text"');
  process.exit(1);
}
// Strip + and spaces so you can also pass “+91 91234 56789”
const recipient = recipientRaw.replace(/[+ ]/g, '');

// ─── Client init ───────────────────────────────────────────
const client = new Client({
  authStrategy: new LocalAuth({ clientId: 'patient-watcher' })
});

client.on('qr', qr => {
  qrcode.generate(qr, { small: true });
  console.log('Scan the QR to authenticate.');
});

// ─── Helpers ───────────────────────────────────────────────
async function gracefulExit(code = 0) {
  try { await client.destroy(); } catch { /* ignore */ }
  process.exit(code);
}

async function send(chat) {
  try {
    const res = await chat.sendMessage(message);
    console.log('Message queued:', res.id.id);
    await new Promise(r => setTimeout(r, 3000));   // wait for sync
    await gracefulExit(0);
  } catch (err) {
    console.error('Failed to send message:', err);
    await gracefulExit(1);
  }
}

// ─── Main flow ─────────────────────────────────────────────
client.on('ready', async () => {
  try {
    const chats = await client.getChats();
    const chat =
      chats.find(c => c.name === recipientRaw) ||      // exact name
      chats.find(c => c.id.user === recipient);        // numeric fallback

    if (!chat) {
      console.error(`Chat "${recipientRaw}" not found.`);
      await gracefulExit(2);
    } else {
      await send(chat);
    }
  } catch (err) {
    console.error('Unexpected error:', err);
    await gracefulExit(3);
  }
});

client.on('auth_failure', m => console.error('Auth failure', m));
client.initialize();
