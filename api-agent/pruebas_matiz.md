# Pruebas del matiz con lo que cuenta el agricultor

Dos soluciones, tres conversaciones de dos turnos cada una, mismo modelo (`gpt-5.4`) y mismo guion. Las soluciones se probaron sin cambiar el código del repositorio (el script modificó el prompt y el resumen solo durante la corrida).

- **Prueba A:** el prompt pide consultar la ficha del cultivo recomendado con `get_crop_profile` y usar un dato concreto.
- **Prueba B:** el motor añade `facts` (mano de obra, riego, ciclo, fertilidad y qué datos faltan) al resultado; el agente no consulta nada más.

# Prueba A: el agente consulta la ficha con get_crop_profile (solo prompt)

## C1 · haba antes, mercado, riego manual, parcela pequeña, comprador de quinua

### Turno 1
**Agricultor:** Antes sembré haba. Quiero ganar más en el mercado. Está a 3588 metros. Riego a mano con manguera, es una parcela pequeña, y ya tengo un comprador de quinua.

**Herramientas:** update_plot, recommend_crop, get_crop_profile

- notas guardadas: `["riego a mano con manguera", "parcela pequeña", "ya tiene un comprador de quinua"]`
- recomendado: Papa; alternativas: ['Cebada']; advertencias: ['lancha', 'nutrientes']
- consultó la ficha de: {'crop': 'papa'}

**Respuesta** (185 palabras):

> Le sugiero sembrar **papa** porque después de haba sí encaja en la rotación y usted está buscando mejor venta en el mercado. La cebada también le puede convenir, y como quedó casi pareja con la papa, usted puede decidir según su semilla, su mercado o su gusto. Después podría seguir con haba, luego cebada y más adelante chocho. Como su parcela es pequeña, tenga en cuenta que la papa tarda más o menos de 6 a 7 meses; ese terreno va a quedar ocupado buen tiempo. Y aunque ya tiene comprador de quinua, la quinua no me sale como opción después de haba en este lote.
> 
> Le aviso dos cosas: el clima de su zona aumenta el riesgo de lancha y la papa puede enfermarse de lancha. También se esperan lluvias fuertes que podrían lavar el nitrógeno del suelo, y en papa ese nutriente puede perderse con la lluvia. Consulte con un experto para una revisión más a detalle. Todavía me falta saber cómo está la tierra; con eso le afino la sugerencia. ¿La tierra es más bien oscura y suelta, o pobre y dura?

### Turno 2
**Agricultor:** ¿Y qué tan difícil es trabajar la papa? ¿Me va a alcanzar el tiempo?

**Herramientas:** ninguna


**Respuesta** (109 palabras):

> La papa sí es de las más trabajosas. Según la guía que tengo para la sierra andina, en una hectárea puede pedir alrededor de 90 jornales, y buena parte del trabajo es manual: siembra, riegos, aporque y cosecha. Por eso, si usted trabaja casi solo, puede quedarle pesada. Ahora, como su parcela es pequeña, puede que sí le alcance el tiempo mejor que en un terreno grande; ahí la decisión depende mucho de cuánta ayuda tenga en la casa. Si quiere algo más liviano de manejar, la cebada suele ser una opción más tranquila. ¿Usted cuenta con ayuda para la siembra y la cosecha, o le toca casi solo?

## C2 · tierra nueva, poco trabajo, sin riego, trabaja con su esposa, media hectárea

### Turno 1
**Agricultor:** Es tierra nueva. Quiero que me dé poco trabajo y ganar algo en el mercado. Está a 3400 metros y no tengo riego, solo lluvia. Trabajo yo solo con mi esposa y es media hectárea.

**Herramientas:** update_plot, recommend_crop, get_crop_profile

- notas guardadas: `["trabaja solo con su esposa", "media hectárea"]`
- recomendado: Chocho (tarwi); alternativas: ['Haba', 'Papa']; advertencias: ['helada']
- consultó la ficha de: {'crop': 'chocho'}

**Respuesta** (179 palabras):

> Le sugiero sembrar **chocho** porque, al ser tierra nueva, entra bien para empezar la rotación y además va más con su idea de poco trabajo y de vender algo. El programa lo pone primero, pero le digo con franqueza que está muy parejo con la haba; si usted ya tuviera semilla o mejor salida para una de las dos, eso puede ayudarle a decidir. Como son media hectárea y trabajan usted y su esposa, también le puede convenir que el chocho suele aguantar bien en secano y su ficha lo ubica dentro del rango de 2 800 a 3 600 metros. Después le sugiero seguir con papa, luego haba y al final cebada. Le aviso una cosa: en su zona se anuncian noches frías, con riesgo de helada, y el chocho es sensible cuando está pequeño y en el eje floral; podría dañarse. Consulte con un experto para una revisión más a detalle. Todavía me falta saber cómo está la tierra; con eso le afino mejor. ¿La tierra se ve más bien oscura y suelta, o pobre y dura?

### Turno 2
**Agricultor:** ¿Y la papa no me conviene más?

**Herramientas:** search_sources, get_crop_profile

- consultó la ficha de: {'crop': 'papa'}

**Respuesta** (135 palabras):

> Puede darle plata, sí, pero para su caso no la veo más conveniente que el chocho. La papa sí entra a esa altura, pero pide bastante más trabajo: en la guía de la FAO para la sierra sale con mano de obra alta, alrededor de 90 jornales por hectárea, y además es un cultivo exigente con la tierra. Como usted trabaja solo con su esposa y el lote es tierra nueva, el chocho le calza mejor para empezar. Además, según esa misma guía, después del chocho la papa suele venir con mejor vigor y con menos pulguilla, o sea primero le ayuda a preparar mejor el lote y luego puede pasar a papa. Si quiere, le afino esto con una sola cosa: ¿la tierra se ve oscura y suelta, o más bien pobre y dura?

## C3 · papa antes, rapidez, poco dinero para abono, vecino sugiere quinua

### Turno 1
**Agricultor:** Antes sembré papa. Quiero cosechar rápido. Estoy a 3200 metros. No tengo mucho dinero para comprar abono. Mi vecino me dijo que mejor siembre quinua.

**Herramientas:** update_plot, recommend_crop, get_crop_profile

- notas guardadas: `["No tengo mucho dinero para comprar abono.", "Su vecino le dijo que siembre quinua."]`
- recomendado: Amaranto / ataco; alternativas: ['Quinua', 'Lizas']; advertencias: ['helada']
- consultó la ficha de: {'crop': 'amaranto'}

**Respuesta** (131 palabras):

> Le sugiero sembrar **amaranto** porque viene bien después de papa y, entre las opciones, entra de las más rápidas. Además, como usted no tiene mucho dinero para abono, le puede convenir que el amaranto no pide tierra muy fértil según la guía. Si prefiere otra opción, también puede mirar la quinua o las lizas; la quinua sí aparece, pero a 3 200 metros queda algo al límite y por eso la veo un poco más arriesgada. Después podría seguir primero con cebada, luego oca y después pasto para que la tierra se recupere. Le aviso una cosa: hay riesgo de helada en su zona y el amaranto no la resiste bien. Todavía me falta saber si usted puede regar en tiempo seco. ¿Tiene riego, aunque sea con manguera, acequia o regadera?

### Turno 2
**Agricultor:** ¿Qué opina de lo que me dijo mi vecino?

**Herramientas:** get_crop_profile

- consultó la ficha de: {'crop': 'quinua'}

**Respuesta** (114 palabras):

> Lo que le dijo su vecino sí tiene sentido. Según la guía de la FAO para cultivos andinos, la quinua puede ir después de papa y su ciclo también es relativamente corto. El detalle es que, a 3 200 metros, ya queda un poco al límite y hay más riesgo con el frío; además, como usted me contó que no quiere gastar mucho en abono, la quinua suele pedir algo más de fertilidad que el amaranto. Por eso le sigo sugiriendo primero **amaranto**, pero le digo con franqueza que están casi empatados y usted puede decidir según semilla, comprador o gusto. Si puede regar en tiempo seco, le afino mejor la sugerencia. ¿Tiene riego?


---

# Prueba B: el resumen del motor trae datos de la ficha (facts)

## C1 · haba antes, mercado, riego manual, parcela pequeña, comprador de quinua

### Turno 1
**Agricultor:** Antes sembré haba. Quiero ganar más en el mercado. Está a 3588 metros. Riego a mano con manguera, es una parcela pequeña, y ya tengo un comprador de quinua.

**Herramientas:** update_plot, recommend_crop

- notas guardadas: `["parcela pequeña", "ya tiene un comprador de quinua"]`
- facts recibidos: `{"mano_de_obra": "muchísima (nivel 5 de 5), unos 90 jornales por hectárea (dato de la FAO)", "ciclo": "6 a 7 meses de siembra a cosecha", "fertilidad": "exigente (alta)", "no_hay_dato": ["riego"]}`
- recomendado: Papa; alternativas: ['Cebada']; advertencias: ['lancha', 'nutrientes']

**Respuesta** (182 palabras):

> Le sugiero sembrar **papa** porque, después de haba, sí encaja bien en la rotación y además usted quiere buscar mejor venta. Como su parcela es pequeña, tenga en cuenta que la papa pide muchísima mano de obra, y por eso la **cebada** también le puede convenir si quiere algo más manejable; la otra opción es **haba**. Después podría seguir primero con haba, luego cebada y después chocho. Con lo que sabemos, voy medio seguro; todavía me falta saber cómo está la fertilidad de la tierra, y con eso le afino mejor.
> 
> Le aviso dos cosas: el clima de su zona aumenta el riesgo de lancha y la papa puede enfermarse de lancha. También se esperan lluvias fuertes que podrían lavar el nitrógeno del suelo, y en papa eso puede afectar la fertilidad; consulte con un experto para una revisión más a detalle.
> 
> Y sobre la quinua, sí ayuda mucho que ya tenga comprador, pero después de haba no me sale como opción para este lote. ¿La tierra es más bien oscura y suelta, o pobre y cansada aunque le ponga poco abono?

### Turno 2
**Agricultor:** ¿Y qué tan difícil es trabajar la papa? ¿Me va a alcanzar el tiempo?

**Herramientas:** ninguna


**Respuesta** (118 palabras):

> La papa sí es trabajosa. Según la guía de la FAO, es de los cultivos que más mano de obra piden, y en la ficha sale como muy alta; además tarda más o menos de 6 a 7 meses desde la siembra hasta la cosecha. En una parcela pequeña puede sí alcanzarle el tiempo, pero depende mucho de si usted trabaja solo o si tiene ayuda en los momentos más pesados. Por eso le digo con franqueza: si lo que más le preocupa es no apurarse tanto, la cebada le puede quedar más llevadera, aunque el programa sigue poniendo primero la **papa** por la rotación y la venta. ¿Usted trabaja ese lote solo o tiene quién le ayude?

## C2 · tierra nueva, poco trabajo, sin riego, trabaja con su esposa, media hectárea

### Turno 1
**Agricultor:** Es tierra nueva. Quiero que me dé poco trabajo y ganar algo en el mercado. Está a 3400 metros y no tengo riego, solo lluvia. Trabajo yo solo con mi esposa y es media hectárea.

**Herramientas:** update_plot, recommend_crop

- notas guardadas: `["Trabaja solo con su esposa.", "Parcela de media hectárea."]`
- facts recibidos: `{"fertilidad": "poco exigente (baja)", "no_hay_dato": ["mano_de_obra", "riego", "ciclo"]}`
- recomendado: Chocho (tarwi); alternativas: ['Haba', 'Papa']; advertencias: ['helada']

**Respuesta** (165 palabras):

> Le sugiero sembrar **chocho** porque en tierra nueva suele ser una buena entrada, y además usted busca poco trabajo y algo que pueda vender. Como trabajan solo usted y su esposa, le conviene mirar un cultivo poco exigente de suelo; aquí el chocho sale como poco exigente. La haba también le sale muy pareja con el chocho, así que están casi empatados y usted puede decidir según semilla, mercado o gusto; otra opción más atrás es la papa. Después podría seguir primero con papa, luego haba y después cebada.
> 
> Le aviso una cosa: en su zona se anuncian noches frías, con riesgo de helada, y el chocho es sensible cuando está pequeño y también en floración. Consulte con un experto para una revisión más a detalle. Todavía me falta saber cómo está la fertilidad de la tierra; con eso le afino mejor la sugerencia. ¿La tierra se ve oscura y suelta, y las plantas crecen bien sin mucho abono, o más bien la nota pobre?

### Turno 2
**Agricultor:** ¿Y la papa no me conviene más?

**Herramientas:** get_crop_profile, search_sources

- consultó la ficha de: {'crop': 'papa'}

**Respuesta** (113 palabras):

> Puede darle mercado, sí, pero para su caso no la veo más conveniente que el chocho. La papa sale más atrás porque pide bastante más trabajo, y usted me dijo que trabajan solo usted y su esposa; según la guía de la FAO para la sierra, es un cultivo de manejo pesado y además suele necesitar suelo bien fértil. También tiene más riesgo de enfermedades como la lancha, y en su zona fría la helada puede pegarle. El chocho, en cambio, sale mejor para arrancar en tierra nueva y es poco exigente con la fertilidad. Si usted quiere, también podemos mirar la haba, que le quedó casi a la par con el chocho.

## C3 · papa antes, rapidez, poco dinero para abono, vecino sugiere quinua

### Turno 1
**Agricultor:** Antes sembré papa. Quiero cosechar rápido. Estoy a 3200 metros. No tengo mucho dinero para comprar abono. Mi vecino me dijo que mejor siembre quinua.

**Herramientas:** update_plot, recommend_crop

- notas guardadas: `["No tiene mucho dinero para comprar abono.", "Su vecino le dijo que siembre quinua."]`
- facts recibidos: `{"riego": "necesita riego", "ciclo": "5 a 7 meses de siembra a cosecha", "fertilidad": "poco exigente (baja)", "no_hay_dato": ["mano_de_obra"]}`
- recomendado: Amaranto / ataco; alternativas: ['Quinua', 'Lizas']; advertencias: ['helada']

**Respuesta** (133 palabras):

> Le sugiero sembrar **amaranto**. Sale primero porque viene bien después de papa y entra entre las opciones más rápidas que tengo para su zona. Como usted no tiene mucho dinero para abono, también le puede convenir porque es poco exigente con la fertilidad. La quinua también le puede servir, y de hecho quedó casi empatada con el amaranto; si usted ya tiene semilla o mejor salida para quinua, vale la pena pensarlo entre esas dos. Después podría seguir con cebada, luego oca y al final pasto para que la tierra se recupere un poco. Le aviso que hay riesgo de helada en su zona y el amaranto no la resiste bien; podría dañarse. Todavía me falta saber si usted puede regar en tiempo seco; con eso le afino mejor la sugerencia. ¿Tiene riego?

### Turno 2
**Agricultor:** ¿Qué opina de lo que me dijo mi vecino?

**Herramientas:** ninguna


**Respuesta** (100 palabras):

> Su vecino no va mal encaminado: la **quinua** sí le sale como opción para después de papa, y quedó casi empatada con el amaranto. Pero a 3 200 metros ya está un poco al filo de la altura que tengo como más segura para quinua, y además con heladas puede sufrir cuando florece. Por eso yo me inclino un poco más por **amaranto** si usted quiere ir a lo más seguro dentro de lo que sabemos. Si usted ya tiene semilla de quinua o sabe que la vende mejor, también puede escoger quinua. ¿Usted tiene cómo regar en tiempo seco?


---

# Prueba final: el código implementado (B con arreglo)

## C1 · haba antes, mercado, riego manual, parcela pequeña, comprador de quinua

### Turno 1
**Agricultor:** Antes sembré haba. Quiero ganar más en el mercado. Está a 3588 metros. Riego a mano con manguera, es una parcela pequeña, y ya tengo un comprador de quinua.

**Herramientas:** update_plot, recommend_crop

- notas guardadas: `["riego a mano con manguera", "parcela pequeña", "ya tengo un comprador de quinua"]`
- facts recibidos: `{"mano_de_obra": "muchísima (nivel 5 de 5), unos 90 jornales por hectárea (dato de la FAO)", "ciclo": "6 a 7 meses de la siembra a la cosecha", "fertilidad": "exigente (alta)", "no_hay_dato": ["riego"]}`
- recomendado: Papa; alternativas: ['Cebada']; advertencias: ['lancha', 'nutrientes']

**Respuesta** (188 palabras):

> Le sugiero sembrar **papa** porque, después de haba, sí entra bien en la rotación y además usted quiere apuntar a mejor venta. También puede mirar la cebada; y aunque ya tiene comprador de quinua, la quinua no me sale como opción después de haba, así que no tengo respaldo para sugerírsela en este momento. Después podría seguir con haba, luego cebada y luego chocho para mover mejor el lote. Como su parcela es pequeña, tenga presente que la papa tarda de 6 a 7 meses desde la siembra hasta la cosecha; y sobre el riego con manguera, no tengo un dato confiable de cuánta agua pide este cultivo, así que eso conviene afinarlo. Le aviso dos cosas: en su zona sube el riesgo de lancha y la papa puede enfermarse; además se esperan lluvias fuertes que pueden lavar el nitrógeno del suelo, y en papa eso puede afectar la fertilidad. Consulte con un experto para una revisión más a detalle. Todavía me falta saber cómo está la tierra; con eso le afino mejor la sugerencia. ¿La tierra se ve oscura y suelta, o más bien pobre y dura?

### Turno 2
**Agricultor:** ¿Y qué tan difícil es trabajar la papa? ¿Me va a alcanzar el tiempo?

**Herramientas:** ninguna


**Respuesta** (107 palabras):

> La papa sí pide bastante trabajo. Según la guía de la FAO, es de los cultivos más pesados en mano de obra: sale como nivel 5 de 5, con unos 90 jornales por hectárea. También ocupa tiempo porque su ciclo va de 6 a 7 meses desde la siembra hasta la cosecha.
> 
> Como su parcela es pequeña, eso le ayuda: no es lo mismo manejar una hectárea que un pedazo corto. Pero si usted busca algo más liviano de trabajar, la papa no sería la opción más descansada. Si quiere, le comparo la papa con la cebada para ver cuál le conviene más por trabajo y tiempo.

## C2 · tierra nueva, poco trabajo, sin riego, trabaja con su esposa, media hectárea

### Turno 1
**Agricultor:** Es tierra nueva. Quiero que me dé poco trabajo y ganar algo en el mercado. Está a 3400 metros y no tengo riego, solo lluvia. Trabajo yo solo con mi esposa y es media hectárea.

**Herramientas:** update_plot, recommend_crop

- notas guardadas: `["Trabajo yo solo con mi esposa.", "Es media hectárea."]`
- facts recibidos: `{"fertilidad": "poco exigente (baja)", "no_hay_dato": ["mano_de_obra", "riego", "ciclo"]}`
- recomendado: Chocho (tarwi); alternativas: ['Haba', 'Papa']; advertencias: ['helada']

**Respuesta** (146 palabras):

> Le sugiero sembrar **chocho** porque es tierra nueva y, según la guía, entra bien para empezar el lote. La haba también le sale casi igual de buena, así que esas dos están muy parejas y usted puede decidir según semilla, gusto o a quién le vende; más atrás queda la papa. Después podría seguir primero con papa, luego con haba y después con cebada. Usted me dijo que trabajan solo su esposa y usted, y eso importa, pero del chocho no tengo un dato confiable de cuánto trabajo pide; además me falta saber cómo está la fertilidad para afinarle mejor. Le aviso una cosa: en su zona se anuncian noches frías, con riesgo de helada, y el chocho puede dañarse cuando está pequeño; consulte con un experto para una revisión más a detalle. ¿La tierra se ve más bien oscura y suelta, o pobre y cansada?

### Turno 2
**Agricultor:** ¿Y la papa no me conviene más?

**Herramientas:** get_crop_profile, search_sources, search_sources

- consultó la ficha de: {'crop': 'papa'}

**Respuesta** (135 palabras):

> Sí puede sembrar papa, pero para lo que usted busca no me convence más que el **chocho**. La papa sí tiene mercado, pero pide bastante más trabajo y más gasto en la práctica; según la guía de la FAO para cultivos andinos, es un cultivo exigente y además suele tener más problema de lancha. En cambio el chocho arranca bien en tierra nueva, aguanta mejor suelo flojo y, según esa misma guía, hasta ayuda a dejar nitrógeno en la tierra para lo que venga después. Como usted trabaja solo con su esposa y no tiene riego, yo me inclino más por **chocho**; pero como haba y chocho quedaron casi empatados, usted decide según la semilla o a quién le vende. Si quiere, le explico cuál de los dos le calza mejor entre chocho y haba.

## C3 · papa antes, rapidez, poco dinero para abono, vecino sugiere quinua

### Turno 1
**Agricultor:** Antes sembré papa. Quiero cosechar rápido. Estoy a 3200 metros. No tengo mucho dinero para comprar abono. Mi vecino me dijo que mejor siembre quinua.

**Herramientas:** update_plot, recommend_crop

- notas guardadas: `["No tengo mucho dinero para comprar abono.", "Mi vecino me dijo que mejor siembre quinua."]`
- facts recibidos: `{"riego": "necesita riego", "ciclo": "5 a 7 meses de la siembra a la cosecha", "no_hay_dato": ["mano_de_obra"], "en_conflicto": {"fertilidad": "la ficha dice «baja», pero un ensayo de Ecuador dice que extrae altas cantidades de nitrógeno"}}`
- recomendado: Amaranto / ataco; alternativas: ['Quinua', 'Lizas']; advertencias: ['helada']

**Respuesta** (138 palabras):

> Le sugiero sembrar **amaranto** porque después de papa sí entra bien en la vuelta del lote y usted quiere cosechar relativamente rápido. La quinua también le sale muy cerca, así que están casi empatadas; como su vecino se la recomendó, también puede ser opción, pero a 3200 metros queda un poco al límite. Después podría seguir con cebada, luego oca y al final pasto para que la tierra descanse. Sobre el abono, le hablo con franqueza: en amaranto las fuentes no coinciden sobre qué tanto exige la fertilidad, así que no quiero adivinar. Le aviso una cosa: hay noches frías con riesgo de helada y el amaranto no resiste bien las heladas; podría dañarse. Consulte con un experto para una revisión más a detalle. Todavía me falta saber si usted puede regar en tiempo seco. ¿Sí o no?

### Turno 2
**Agricultor:** ¿Qué opina de lo que me dijo mi vecino?

**Herramientas:** get_crop_profile, search_sources

- consultó la ficha de: {'crop': 'quinua'}

**Respuesta** (110 palabras):

> Su vecino no va mal encaminado. La quinua sí puede ir después de papa, y según la guía de la FAO es un cultivo muy usado en esa rotación. El detalle en su caso es la altura: a 3200 metros ya queda algo al límite para varias quinuas de valle, y si le caen heladas en floración puede sufrir. Por eso yo sigo viendo un poquito mejor el **amaranto** para usted: está justo en su rango de altura y también sale bien para un ciclo relativamente corto. De todas maneras, como quedaron casi empatados, si usted ya tiene semilla de quinua o mejor salida para venderla, también la puede considerar.

