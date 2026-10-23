import assert from 'node:assert/strict';
import {generateKey,encrypt,decrypt,modPow,inverse,toCents} from '../web/paillier.js';
const key=await generateKey();
let passed=0;
function check(name,fn){fn();passed++;console.log('PASS '+name);}
check('2048-bit browser key',()=>assert.equal(key.n.toString(2).length,2048));
check('exact decimal money conversion',()=>{for(const [raw,want] of [['0',0],['0.01',1],['1.2',120],['1240.00',124000],['10000.00',1000000]])assert.equal(toCents(raw),want);});
check('reject unsafe decimal input',()=>{for(const raw of ['1e3','-1','NaN','1.234','10000.01','01.0','1,200',' 2','2 ',{},''])assert.throws(()=>toCents(raw));});
check('round-trip accepted endpoints',()=>{for(const value of [0,1,124000,1000000])assert.equal(decrypt(encrypt(value,key),key),value);});
check('ciphertexts are independently randomized',()=>assert.notEqual(encrypt(123,key),encrypt(123,key)));
check('homomorphic sum and negative difference',()=>{const a=encrypt(124000,key),b=encrypt(186000,key);assert.equal(decrypt(a*b%key.n2,key),310000);assert.equal(decrypt(a*inverse(b,key.n2)%key.n2,key),-62000);});
check('public scalar multiplication',()=>assert.equal(decrypt(modPow(encrypt(124000,key),3n,key.n2),key),372000));
check('reject invalid plaintext and group elements',()=>{for(const value of [-1,1.2,1000001,Infinity,'123'])assert.throws(()=>encrypt(value,key));for(const c of [0n,key.n,key.n2,-1n])assert.throws(()=>decrypt(c,key));});
console.log(JSON.stringify({suite:'browser-paillier-and-money',passed,key_bits:2048}));
