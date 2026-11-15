# CLAUDE.md

## Git hooks

El repo trae un hook `commit-msg` en `.githooks/` que quita de los mensajes de commit los trailers `Co-Authored-By` que mencionan a Claude o Anthropic (los coautores humanos se mantienen).

Antes de hacer el primer commit en un clon, verifica que esté activo y, si no lo está, actívalo:

```bash
git config core.hooksPath          # debe imprimir .githooks
git config core.hooksPath .githooks
```
