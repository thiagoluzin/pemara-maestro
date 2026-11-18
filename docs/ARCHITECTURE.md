# Arquitetura

```text
imagem + intenção
       |
       v
Anchor Intelligence -- divergência bloqueante --> decisão humana
       |
       v
contrato hash-bound
       |
       +--> compilador H3 ----+
       |                      |
       +--> compilador LTX25 -+--> workflow descriptor --> executor local
                                      |
                                      +--> lease GPU
                                      +--> QC técnico
                                      +--> revisão humana
```

O registry rejeita seleção vazia, motores removidos e qualquer tentativa de
modo automático. Readiness vem de uma atestação local; nunca é deduzido pela
presença deste código.

O contrato de âncora separa:

- evidência realmente visível;
- intenção declarada;
- invariantes;
- mudanças explicitamente permitidas;
- restrições negativas;
- plano temporal e câmera;
- divergências que exigem decisão.
