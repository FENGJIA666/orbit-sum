// Paillier additive homomorphic arithmetic. All private-key operations stay here.
export const gcd = (a, b) => { while (b) [a, b] = [b, a % b]; return a; };
export function toCents(input) {
  if (typeof input !== 'string' || !/^(0|[1-9][0-9]{0,4})(\.[0-9]{1,2})?$/.test(input)) throw new Error('Enter an amount from 0.00 to 10,000.00, with up to two decimal places.');
  const [whole, fraction=''] = input.split('.');
  const cents = BigInt(whole)*100n + BigInt(fraction.padEnd(2,'0'));
  if (cents > 1000000n) throw new Error('Enter an amount from 0.00 to 10,000.00.');
  return Number(cents);
}
export function modPow(base, exponent, modulus) {
  if (exponent < 0n || modulus <= 1n) throw new Error('Invalid modular exponent');
  let result = 1n;
  base = ((base % modulus) + modulus) % modulus;
  while (exponent) {
    if (exponent & 1n) result = result * base % modulus;
    base = base * base % modulus;
    exponent >>= 1n;
  }
  return result;
}
export function inverse(a, modulus) {
  let [oldR, r, oldS, s] = [a, modulus, 1n, 0n];
  while (r) { const q = oldR / r; [oldR, r] = [r, oldR - q * r]; [oldS, s] = [s, oldS - q * s]; }
  if (oldR !== 1n) throw new Error('Non-invertible element');
  return (oldS % modulus + modulus) % modulus;
}
function fromBase64Url(value) {
  return BigInt('0x' + Array.from(atob(value.replace(/-/g, '+').replace(/_/g, '/')), x => x.charCodeAt(0).toString(16).padStart(2, '0')).join(''));
}
export async function generateKey() {
  // WebCrypto supplies independently generated RSA primes using native CSPRNG.
  // They are used to construct Paillier parameters; RSA is never used on data.
  const pair = await crypto.subtle.generateKey({name:'RSA-OAEP',modulusLength:2048,publicExponent:new Uint8Array([1,0,1]),hash:'SHA-256'}, true, ['encrypt','decrypt']);
  const jwk = await crypto.subtle.exportKey('jwk', pair.privateKey);
  const p = fromBase64Url(jwk.p), q = fromBase64Url(jwk.q), n = p * q;
  const lambda = (p - 1n) / gcd(p - 1n, q - 1n) * (q - 1n);
  return {n, n2:n*n, g:n+1n, lambda, mu:inverse(lambda,n)};
}
export function encrypt(value, key) {
  if (!Number.isSafeInteger(value) || value < 0 || value > 1000000) throw new Error('Use whole-number values from 0 to 1,000,000');
  const size = Math.ceil(key.n.toString(2).length / 8);
  let r;
  do {
    const bytes = crypto.getRandomValues(new Uint8Array(size));
    r = BigInt('0x'+Array.from(bytes,x=>x.toString(16).padStart(2,'0')).join(''));
  } while (r < 1n || r >= key.n || gcd(r,key.n) !== 1n);
  return ((1n + BigInt(value) * key.n) * modPow(r,key.n,key.n2)) % key.n2;
}
export function decrypt(ciphertext, key) {
  const c = BigInt(ciphertext);
  if (c < 1n || c >= key.n2 || gcd(c,key.n) !== 1n) throw new Error('Invalid ciphertext');
  let m = ((modPow(c,key.lambda,key.n2)-1n)/key.n * key.mu) % key.n;
  if (m > key.n/2n) m -= key.n;
  if (m > BigInt(Number.MAX_SAFE_INTEGER) || m < BigInt(Number.MIN_SAFE_INTEGER)) throw new Error('Result exceeds supported integer range');
  return Number(m);
}
