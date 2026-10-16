-- Laboratorio #8, Etapa 1 (paso 1.3): crea la base de datos y tu registro.
-- Solo cambia la última línea (CAMBIA-...) con tus datos de estudiante.json.
-- Deja 'TEMP0000' hasta el paso 3.4 del README; luego pon tu código real y ejecuta de nuevo.

DROP DATABASE IF EXISTS lab8_web;
CREATE DATABASE lab8_web CHARACTER SET utf8mb4;
USE lab8_web;

CREATE TABLE estudiantes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cedula VARCHAR(20) NOT NULL UNIQUE,
    nombre VARCHAR(60) NOT NULL,
    apellido VARCHAR(60) NOT NULL,
    codigo VARCHAR(8) NOT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO estudiantes (cedula, nombre, apellido, codigo)
VALUES ('CAMBIA-TU-CEDULA', 'CAMBIA-TU-NOMBRE', 'CAMBIA-TU-APELLIDO', 'TEMP0000');
