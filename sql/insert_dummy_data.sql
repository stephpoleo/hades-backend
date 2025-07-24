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

-- Insertar plazas
INSERT INTO "Plaza" ("name", "state", "municipality", "zip_code", "plaza_status", "plaza_phone") VALUES
('QUERETARO', 'Queretaro', 'Bernardo Quintana', '76230', TRUE, 442123456),
('NUEVO LEON', 'Nuevo León', 'San Pedro', '66200', TRUE, 818765432),
('ESTADO DE MEXICO', 'Estado de Mexico', 'Guadalupe', '67100', TRUE, 555987654);

-- Insertar EDS (Estaciones de Servicio)
INSERT INTO "EDS" ("name", "id_plaza_fk") VALUES
('EDS 5 de Febrero', 1),
('EDS Ecatepec', 3),
('EDS Colón', 2);

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
INSERT INTO "FormAnswers" ("id_question_form_fk", "answer") VALUES
(1, 'Sí'),
(2, 'Equipo en buen estado general, sin anomalías visibles'),
(3, '10'),
(1, 'Sí'),
(2, 'Se detectó ruido anormal en compresor'),
(3, '7'),
(1, 'Sí'),
(2, 'Sistema de seguridad funcionando correctamente'),
(3, '9'),
(1, 'No'),
(2, 'Fugas menores en la válvula de seguridad'),
(3, '5');

-- Crear índices para optimizar consultas
CREATE INDEX IF NOT EXISTS idx_users_email ON "Users"("email");
CREATE INDEX IF NOT EXISTS idx_users_role ON "Users"("id_role_fk");
CREATE INDEX IF NOT EXISTS idx_work_order_status ON "WorkOrder"("status");
CREATE INDEX IF NOT EXISTS idx_work_order_date ON "WorkOrder"("date");
CREATE INDEX IF NOT EXISTS idx_work_order_user ON "WorkOrder"("id_usr_fk");
CREATE INDEX IF NOT EXISTS idx_work_order_eds ON "WorkOrder"("id_eds_fk");
CREATE INDEX IF NOT EXISTS idx_eds_plaza ON "EDS"("id_plaza_fk");
CREATE INDEX IF NOT EXISTS idx_form_answers_question ON "FormAnswers"("id_question_form_fk");
