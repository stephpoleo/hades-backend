-- Datos dummy para la base de datos Hades
-- Ejecutar después de crear las tablas

-- Insertar permisos
INSERT INTO "Permissions" ("name", "permission_status") VALUES
('create_users', TRUE),
('read_users', TRUE),
('update_users', TRUE),
('delete_users', TRUE);

-- Insertar roles
INSERT INTO "Roles" ("name", "id_permission_fk", "role_status") VALUES
('Administrador', 1, TRUE),
('Operador', 2, TRUE);

-- Insertar EDS (Estaciones de Servicio)
INSERT INTO "EDS" ("name", "plaza", "state", "municipality", "zip_code", "plaza_status", "long_eds", "latit_eds") VALUES
('EDS 5 de Febrero', 'QUERETARO', 'Queretaro', 'Bernardo Quintana', '76230', TRUE, -100.389, 20.589),
('EDS Ecatepec', 'ESTADO DE MEXICO', 'Estado de Mexico', 'Guadalupe', '67100', TRUE, -99.063, 19.601),
('EDS Colón', 'NUEVO LEON', 'Nuevo León', 'San Pedro', '66200', TRUE, -100.355, 25.653);

-- Insertar usuarios
INSERT INTO "Users" ("name", "email", "password", "usr_status", "id_role_fk", "id_eds_fk") VALUES
('Juan Pérez', 'juan.perez@natgas.com.mx', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewReNGdWBGu6TQFu', TRUE, 1, 1),
('María González', 'maria.gonzalez@natgas.com.mx', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewReNGdWBGu6TQFu', TRUE, 2, 1),
('Carlos Rodríguez', 'carlos.rodriguez@natgas.com.mx', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewReNGdWBGu6TQFu', TRUE, 2, 3),
('Ana López', 'ana.lopez@natgas.com.mx', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewReNGdWBGu6TQFu', TRUE, 2, 2);

-- Insertar preguntas de formulario
INSERT INTO "FormQuestions" ("question", "is_required", "type") VALUES
('¿Se completó la inspección visual?', TRUE, 'boolean'),
('Describa el estado general del equipo', FALSE, 'text'),
('Calificación general del 1 al 10', TRUE, 'number');

-- Insertar órdenes de trabajo
INSERT INTO "WorkOrder" ("status", "id_usr_fk", "id_eds_fk", "dsc", "image", "id_question_form_fk", "name") VALUES
('pending', 3, 1, 'Inspección rutinaria mensual de equipos de gas natural', 'inspeccion_001.jpg', 1, 'Inspección EDS 5 de Febrero'),
('in_progress', 4, 2, 'Mantenimiento preventivo del compresor principal', 'mantenimiento_001.jpg', 2, 'Mantenimiento EDS Colón'),
('completed', 1, 3, 'Verificación de sistema de seguridad tras reporte', 'seguridad_001.jpg', 3, 'Verificación EDS Ecatepec'),
('pending', 2, 1, 'Inspección de fugas reportadas por cliente', 'fugas_001.jpg', 1, 'Inspección EDS 5 de Febrero');

-- Insertar respuestas de formulario
INSERT INTO "FormAnswers" ("id_question_form_fk", "answer", "area", "comments", "image") VALUES
(1, TRUE, 'Compresión', 'Revisión completa realizada sin inconvenientes', 'foto1.jpg'),
(2, NULL, 'Compresión', 'Equipo en buen estado general, sin anomalías visibles', 'foto2.jpg'),
(3, NULL, 'Compresión', '10', 'foto3.jpg'),
(1, TRUE, 'Almacenamiento', 'Se detectó ruido anormal en compresor', 'foto4.jpg'),
(2, NULL, 'Almacenamiento', 'Sistema de seguridad funcionando correctamente', 'foto5.jpg'),
(3, NULL, 'Almacenamiento', '7', 'foto6.jpg'),
(1, TRUE, 'Distribución', 'Fugas menores en la válvula de seguridad', 'foto7.jpg'),
(2, NULL, 'Distribución', 'Sistema de seguridad funcionando correctamente', 'foto8.jpg'),
(3, NULL, 'Distribución', '9', 'foto9.jpg'),
(1, FALSE, 'Mantenimiento', 'Fugas menores en la válvula de seguridad', 'foto10.jpg'),
(2, NULL, 'Mantenimiento', 'Fugas menores en la válvula de seguridad', 'foto11.jpg'),
(3, NULL, 'Mantenimiento', '5', 'foto12.jpg');

-- Crear índices para optimizar consultas
CREATE INDEX IF NOT EXISTS idx_users_email ON "Users"("email");
CREATE INDEX IF NOT EXISTS idx_users_role ON "Users"("id_role_fk");
CREATE INDEX IF NOT EXISTS idx_work_order_status ON "WorkOrder"("status");
CREATE INDEX IF NOT EXISTS idx_work_order_date ON "WorkOrder"("date");
CREATE INDEX IF NOT EXISTS idx_work_order_user ON "WorkOrder"("id_usr_fk");
CREATE INDEX IF NOT EXISTS idx_work_order_eds ON "WorkOrder"("id_eds_fk");
CREATE INDEX IF NOT EXISTS idx_eds_plaza ON "EDS"("plaza");
CREATE INDEX IF NOT EXISTS idx_form_answers_question ON "FormAnswers"("id_question_form_fk");
