import { Client, LocalAuth } from 'whatsapp-web.js';
import qrcode from 'qrcode-terminal';

const [,, recipient, ...msgParts] = process.argv;
const message = msgParts.join(' ');
if (!recipient || !message) {
    console.error('Usage: node send_whatsapp.js "Recipient Name" "Message text"');
    process.exit(1);
}

const client = new Client({
    authStrategy: new LocalAuth({ clientId: 'patient-watcher' })
});

client.on('qr', qr => {
    qrcode.generate(qr, { small: true });
    console.log('Scan the QR code above in WhatsApp to authenticate.');
});

client.on('ready', async () => {
    try {
        const chats = await client.getChats();
        const chat = chats.find(c => c.name === recipient);
        if (!chat) {
            console.error(`Chat "${recipient}" not found.`);
        } else {
            await chat.sendMessage(message);
            console.log('Message sent:', message);
        }
    } catch (err) {
        console.error('Failed to send message:', err);
    } finally {
        await client.destroy();
        process.exit(0);
    }
});

client.on('auth_failure', m => console.error('Auth failure', m));
client.initialize();
