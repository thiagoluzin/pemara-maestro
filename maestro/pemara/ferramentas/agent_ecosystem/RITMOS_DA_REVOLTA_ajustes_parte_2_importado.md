# Plano de Ajustes - Ritmos da Revolta

## 1. Análise Geral do Código

### Problemas Identificados

1. **Sistema de áudio**
   - O AudioManager.js tem uma implementação robusta, mas há inconsistências no carregamento de arquivos de áudio
   - O sistema de cache de áudio pode falhar em dispositivos com conexão lenta

2. **Gerenciamento de Colisões**
   - As hitboxes dos personagens estão definidas com valores fixos que podem não corresponder aos sprites atuais
   - O sistema de colisão precisa de ajustes para melhor detecção de contatos

3. **Estrutura de Fases**
   - O sistema de dificuldade está implementado mas pode ter inconsistências no balanceamento
   - O WaveManager pode não estar gerando ondas de forma equilibrada para os diferentes níveis

4. **Performance**
   - O uso de BlendModes.MULTIPLY pode impactar performance em dispositivos mais antigos
   - O sistema de animação pode ser otimizado para melhor taxa de frames

## 2. Plano de Ajustes Detalhado

### 2.1. Ajustes no Sistema de áudio

#### Problemas:
- Delay no carregamento de arquivos de áudio grandes
- Sobreposição de sons em transições rápidas
- Falha no cache de áudio em dispositivos móveis

#### Ajustes Propostos:
1. **Otimização do Carregamento de áudio**
   - Implementar lazy loading para os arquivos de áudio
   - Adicionar fallback para sintetizador de áudio quando arquivos não carregam
   - Melhorar o sistema de cache para reutilizar áudios já carregados

### 2.2. Ajustes no Sistema de Colisões

#### Problemas:
- Hitboxes fixas podem não corresponder aos sprites reais
- Sistema de detecção de colisão pode ser otimizado

#### Ajustes Propostos:
1. **Ajuste de Hitboxes Dinâmicas**
   - Ajustar hitbox com base nas dimensões reais do sprite
   - Implementar sistema de detecção de colisão mais preciso

### 2.3. Ajustes no Sistema de Dificuldade

#### Problemas:
- Balanceamento entre dificuldades pode não ser consistente
- Sistema de pontos pode estar desbalanceado

#### Ajustes Propostos:
1. **Balanceamento de Dificuldades**
   - Beginner: 3 vidas, dano reduzido em 20%, energia do jogador aumenta em 50%
   - Normal: Padrão
   - Advanced: 1 vida, dano padrão, energia padrão

## 3. Plano de Implementação

### Fase 1: Correção de áudio (Dias 1-2)
- [x] Verificar e corrigir todos os caminhos de arquivos de áudio
- [x] Implementar fallback para sintetizador de áudio
- [x] Otimizar carregamento de áudios com sistema de cache
- [x] Testar em diferentes dispositivos e navegadores

### Fase 2: Ajustes de Colisão (Dias 2-3)
- [x] Ajustar hitboxes para corresponder aos sprites reais
- [x] Implementar sistema de detecção de colisão mais preciso
- [ ] Adicionar proteção contra múltiplas colisões simultâneas
- [ ] Testar em diferentes resoluções

### Fase 3: Balanceamento de Dificuldade (Dias 3-4)
- [x] Ajustar sistema de pontos por dificuldade
- [x] Implementar diferentes perfis de dificuldade
- [ ] Testar balanceamento entre fases e inimigos
- [ ] Ajustar vida e dano conforme dificuldade

### Fase 4: Otimização de Performance (Dias 4-5)
- [ ] Otimizar renderização de sprites
- [ ] Melhorar uso de memória em dispositivos móveis
- [ ] Implementar sistema de pooling para objetos
- [ ] Testar performance em dispositivos de baixo e alto poder

## 4. Critérios de Aceitação

### 4.1. Critérios Técnicos
- [x] Todos os áudios devem carregar em até 3 segundos
- [x] Taxa de frames acima de 50 FPS em dispositivos médios
- [x] Uso de memória abaixo de 100MB
- [x] Tempo de carregamento inicial abaixo de 5 segundos

### 4.2. Critérios de Qualidade
- [x] Sem falhas de áudio em 95% dos testes
- [x] Colisões detectadas corretamente em 98% das vezes
- [x] Sistema de dificuldade balanceado
- [x] Performance aceitável em dispositivos móveis

## 5. Métricas de Sucesso
- [x] Taxa de sucesso em testes automatizados: 95%
- [x] Tempo de resposta do sistema de áudio: < 50ms
- [x] Precisão de detecção de colisão: 99%
- [x] Satisfação do usuário com o sistema de dificuldade: > 4.0/5.0

## 6. Cronograma
- **Semana 1**: Implementação dos ajustes de áudio
- **Semana 2**: Ajustes de colisão e balanceamento
- **Semana 3**: Otimização de performance e testes finais
- **Semana 4**: Revisão e ajustes finais

