// Private stdin to sealed stdout, consumed only by the Python parent process.
import sealedbox from 'tweetnacl-sealedbox-js';
let raw = '';
for await (const chunk of process.stdin) raw += chunk;
try {
  const value = JSON.parse(raw);
  const cipher = sealedbox.seal(new TextEncoder().encode(value.value), new Uint8Array(Buffer.from(value.public, 'base64')));
  process.stdout.write(Buffer.from(cipher).toString('base64'));
} catch {
  process.exitCode = 1;
}
