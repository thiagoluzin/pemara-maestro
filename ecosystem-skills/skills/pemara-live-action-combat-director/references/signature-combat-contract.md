# Contrato de combate assinatura

Use esta estrutura junto ao workflow `h3_live_action_signature_combat`.

## Matriz por personagem

```json
{
  "id": "character_id",
  "combatPersonality": "ritmo, guarda, distância e intenção corporal",
  "visualSignature": "sinal reconhecível durante a ação",
  "ownedMechanics": ["move_id", "weapon_or_power_id"],
  "forbiddenMechanics": ["move_or_power_that_belongs_to_someone_else"]
}
```

`ownedMechanics` e `forbiddenMechanics` não podem se sobrepor. Todos os personagens da matriz de identidade visual devem aparecer na matriz de combate.

## Contrato por microtake

```json
{
  "moveId": "owned_move_id",
  "ownerId": "attacker_id",
  "opponentId": "defender_id",
  "canonicalMechanic": "como o corpo ou arma realmente executa o golpe",
  "outcome": "mudança física e dramática observável",
  "cutMotivation": "movimento que entrega o corte",
  "modelMayChooseDifferentMove": false,
  "dominantExchangeCount": 1,
  "physicsChain": {
    "anticipation": "carregamento visível",
    "propulsion": "origem e vetor da força",
    "contact": "contato, bloqueio ou evasão legível",
    "displacement": "mudança dos centros de massa",
    "reaction": "resposta involuntária e ambiental",
    "recovery": "consequência ainda em movimento"
  },
  "effectLifecycle": {
    "type": "none | energy | fire | ice | weapon | hybrid",
    "ownerId": "same_as_move_owner",
    "attachment": "corpo ou objeto ao qual permanece ligado",
    "onset": "causa e instante de surgimento",
    "trajectory": "vetor acompanhado",
    "contact": "resposta no contato",
    "decay": "como e quando desaparece",
    "environmentalConsequence": "luz, calor, água, lama ou destroços afetados",
    "forbiddenTransfers": ["efeito no personagem errado"]
  },
  "readability": {
    "contactVisible": true,
    "attackVectorReadable": true,
    "cutawayAtImpact": false,
    "cameraShakeCarriesImpact": false
  }
}
```

## Aplicação Cage versus Scorpion

Neste projeto específico:

- Johnny Cage possui `shadow_kick`, `shadow_uppercut`, `green_forceball` e `split_low_strike`; a energia verde nasce da técnica e acompanha corpo ou projétil até contato e dissipação.
- Scorpion possui `chain_kunai_spear`, `teleport_counter`, `hellfire_burst` e `hellfire_sweep`; kunai, corrente, teleporte e hellfire mantêm origem e propriedade legíveis.
- Johnny não recebe hellfire, corrente ou gelo. Scorpion não recebe energia verde nem gelo.
- Um clarão verde genérico ou fogo decorativo não cumpre cobertura de golpe assinatura.
