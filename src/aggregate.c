/* Keyless Paillier evaluation with OpenSSL BIGNUM. Input: n, count, (c, weight). */
#include <openssl/bn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int decimal(const char *s) {
    if (!*s) return 0;
    for (; *s; ++s) if (*s < '0' || *s > '9') return 0;
    return 1;
}

int main(void) {
    char raw[1235]; int count = 0, weight = 0, ok = 0;
    BN_CTX *ctx = BN_CTX_new();
    BIGNUM *n = NULL, *c = NULL, *n2 = BN_new(), *acc = BN_new(), *term = BN_new(), *gcd = BN_new();
    if (!ctx || !n2 || !acc || !term || !gcd) goto done;
    if (scanf("%1234s",raw) != 1 || !decimal(raw) || !BN_dec2bn(&n,raw)) goto done;
    if (BN_num_bits(n) != 2048 || !BN_is_odd(n) || !BN_sqr(n2,n,ctx) || !BN_one(acc)) goto done;
    if (scanf("%d",&count) != 1 || count < 2 || count > 32) goto done;
    for (int i = 0; i < count; ++i) {
        if (scanf("%1234s %d",raw,&weight) != 2 || !decimal(raw) || (weight != 1 && weight != -1)) goto done;
        if (!BN_dec2bn(&c,raw) || BN_is_zero(c) || BN_cmp(c,n2) >= 0 || !BN_gcd(gcd,c,n,ctx) || !BN_is_one(gcd)) goto done;
        if (weight == -1) { if (!BN_mod_inverse(term,c,n2,ctx)) goto done; }
        else if (!BN_copy(term,c)) goto done;
        if (!BN_mod_mul(acc,acc,term,n2,ctx)) goto done;
    }
    char *out = BN_bn2dec(acc);
    if (!out) goto done;
    puts(out); OPENSSL_free(out); ok = 1;
done:
    BN_free(n); BN_free(c); BN_free(n2); BN_free(acc); BN_free(term); BN_free(gcd); BN_CTX_free(ctx);
    if (!ok) fputs("Invalid encrypted evaluation input.\n",stderr);
    return ok ? 0 : 1;
}
