# Reflexión (Etapa 4)

Responde con tus palabras (mínimo 40 palabras por respuesta). Ver README, Etapa 4.

## Pregunta 1

Mi código personal es 4e5d7a80, este valor es de tipo string porque se obtiene mediante la función substr(), que extrae una parte de una cadena de texto y devuelve otra cadena. Si intentaramos utilizar esta variable en una suma PHP intentaría convertirlo a un valor numérico, pero "4e5d7a80" no es una cadena numérica decimal válida para una suma. Por eso, en PHP 8.2, una operación como esta produciría un TypeError.

## Pregunta 2

En este escenario $precio aparece como double en gettype() como consecuencia de la lógica aplicada en PHP al momento de calcular el resultado de una división. La comparación de 0.1 + 0.2 == 0.3 es falsa porque PHP representa los números decimales mediante valores binarios de punto flotante. Algunos números, como 0.1 y 0.2, no pueden representarse exactamente en ese formato, lo que produce pequeñas diferencias de precisión. $n1 es de tipo integer, lo que significa que su valor solo contiene un entero, sin parte decimal. La principal diferencia entre intdiv y / es que / realiza la división y puede devolver decimales, mientras que intdiv solamente devuelve la parte entera.

## Pregunta 3

La diferencia entre define() y const es que ambas permiten declarar constantes en PHP, pero define() es una función que se ejecuta durante el programa, mientras que const es una palabra clave que permite declarar una constante directamente en el código. Al intentar redefinir SEMILLA_LAB8 con otro valor, obtuve false, porque PHP no permite modificar una constante que ya fue definida. El símbolo @ evitó que apareciera una advertencia, pero no permitió cambiar su valor original.

Esta prueba la realicé utilizando PHP 8.2.12 y Apache 2.4.58 (Win64), instalados mediante XAMPP en Windows 11.