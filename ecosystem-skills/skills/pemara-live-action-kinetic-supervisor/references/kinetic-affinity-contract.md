# Contrato de afinidade cinética

Registre o final útil de A e o início útil de B a partir de intervalos com movimento antes e depois do quadro de borda.

## Estado de cada personagem

```json
{
  "characterId": "id",
  "screenPosition": "posição nos três eixos da geografia",
  "rootVector": "direção do centro de massa",
  "speedClass": "slow | medium | fast",
  "weightBearingFoot": "left | right | both | airborne",
  "torsoAngularDirection": "sentido e fase de rotação",
  "limbPhase": "carregando | estendendo | contato | retraindo | recuperando",
  "gazeTarget": "alvo real",
  "contactState": "corpo, chão, arma ou objeto em contato",
  "damageFatigueState": "dano e fadiga que persistem"
}
```

`speedClass` nunca pode ser `still` numa fronteira declarada móvel.

## Estado dos demais canais

```json
{
  "camera": {
    "positionAndLens": "posição, altura e lente",
    "translationVector": "direção da câmera física",
    "speedClass": "slow | medium | fast",
    "angularPhase": "sentido de arco/pan e fase",
    "foregroundOcclusion": "elemento físico e duração, ou none"
  },
  "objectEffects": [
    {
      "id": "weapon_or_effect",
      "ownerId": "character_id",
      "anchorPoint": "mão, corpo, chão ou cenário",
      "vectorAndSpeed": "movimento",
      "tensionOrLifecyclePhase": "tenso, solto, surgindo, contato, dissipando"
    }
  ],
  "environment": {
    "persistentDamage": "dano já existente",
    "movingElements": "água, chuva, folhas, tecido, destroços",
    "foreground": "estado e vetor",
    "midground": "estado e vetor",
    "background": "estado e vetor"
  }
}
```

## Decisão

Para cada canal, use somente:

- `MATCH`: B continua A sem recomposição.
- `RECOVERABLE_BY_CAUSAL_CONNECTOR`: existe uma ação física curta e irreversível que resolve a diferença sem reset.
- `SOURCE_REGEN_REQUIRED`: a diferença contradiz a ação, identidade ou mundo.

Um único `SOURCE_REGEN_REQUIRED` em centro de massa, pé de apoio, fase do golpe, alvo, câmera/geografia, arma/poder ou dano persistente bloqueia a junção.

## Regra prática

Se o primeiro segundo de B precisar fazer o personagem “voltar para a posição certa”, B está errado. Se o conector servir apenas para centralizar atores ou esconder a troca, regenere a fonte. Se todos os vetores continuam, prefira o corte cinético direto e preserve os bitstreams aprovados.
