-- === DUMMY DATA PARA ROLES Y PERMISOS ===

-- Permisos
INSERT INTO "Permissions" ("id_permissions_pk", "name", "created_at", "updated_at", "usr_created_at", "usr_updated_at", "permission_status") VALUES
	(1, 'read_forms', '2025-09-07', '2025-09-07', 'system', 'system', TRUE),
	(2, 'answer_forms', '2025-09-07', '2025-09-07', 'system', 'system', TRUE),
	(3, 'crud_forms', '2025-09-07', '2025-09-07', 'system', 'system', TRUE),
	(4, 'crud_users', '2025-09-07', '2025-09-07', 'system', 'system', TRUE);

-- Roles
INSERT INTO "Roles" ("id_rol_pk", "name", "created_at", "updated_at", "usr_created_at", "usr_updated_at", "role_status") VALUES
	(1, 'usuario', '2025-09-07', '2025-09-07', 'system', 'system', TRUE),
	(2, 'administrador', '2025-09-07', '2025-09-07', 'system', 'system', TRUE);

-- Relacionar roles con permisos
INSERT INTO "Roles_permissions" ("roles_id", "permissions_id") VALUES
	(1, 1), -- usuario: read_assigned_forms
	(1, 2), -- usuario: answer_assigned_forms
	(2, 1), -- admin: read_assigned_forms
	(2, 2), -- admin: answer_assigned_forms
	(2, 3), -- admin: crud_forms
	(2, 4); -- admin: crud_users


-- === DUMMY DATA PARA EDS, USUARIOS, PLANTILLAS, PREGUNTAS, ORDENES DE TRABAJO Y RESPUESTAS ===
INSERT INTO "Users" ("name", "email", "password", "usr_status", "id_eds_fk", "id_role_fk") VALUES
	('Stephanie Poleo', 'stephanie.poleo@natgas.com.mx', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewReNGdWBGu6TQFu', TRUE, 1, 2);

INSERT INTO "EDS" ("name", "plaza", "state", "municipality", "zip_code", "plaza_status", "long_eds", "latit_eds") VALUES
('EDS 5 de Febrero', 'QUERETARO', 'Queretaro', 'Bernardo Quintana', '76230', TRUE, -100.389, 20.589),
('EDS Ecatepec', 'ESTADO DE MEXICO', 'Estado de Mexico', 'Guadalupe', '67100', TRUE, -99.063, 19.601),
('EDS Colón', 'NUEVO LEON', 'Nuevo León', 'San Pedro', '66200', TRUE, -100.355, 25.653);

INSERT INTO "Users" ("name", "email", "password", "usr_status", "id_eds_fk") VALUES
('Juan Pérez', 'juan.perez@natgas.com.mx', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewReNGdWBGu6TQFu', TRUE, 1),
('María González', 'maria.gonzalez@natgas.com.mx', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewReNGdWBGu6TQFu', TRUE, 1),
('Carlos Rodríguez', 'carlos.rodriguez@natgas.com.mx', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewReNGdWBGu6TQFu', TRUE, 3),
('Ana López', 'ana.lopez@natgas.com.mx', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewReNGdWBGu6TQFu', TRUE, 2);

INSERT INTO "FormTemplate" ("name", "description", "created_at", "updated_at", "is_active") VALUES
('F-PRO-OPE-013 (F) MANTENIMIENTO AUTÓNOMO SURTIDORES EDS FIJAS', 'Formulario para mantenimiento autónomo de surtidores en estaciones de servicio fijas', '2024-01-01', '2024-01-01', TRUE),
('F-PRO-OPE-013 (L) REVISION BAÑO CABALLEROS', 'Formulario para revisión de baño de caballeros en estaciones de servicio', '2024-01-01', '2024-01-01', TRUE);

INSERT INTO "WorkOrder" (
	"date", "status", "user_id", "eds_id", "form_template_id", "start_date_time", "end_date_time", "work_area_id"
) VALUES
('2024-01-15', 'completed', 1, 1, 1, '2024-01-15 07:41:00', '2024-01-15 07:43:00', NULL),
('2024-01-20', 'completed', 2, 2, 1, '2024-01-20 08:15:00', '2024-01-20 08:45:00', NULL),
('2024-01-10', 'completed', 3, 3, 1, '2024-01-10 09:30:00', '2024-01-10 10:15:00', NULL),
('2024-01-25', 'pending', 4, 1, 1, '2024-01-25 14:00:00', NULL, NULL),
('2024-01-18', 'completed', 2, 1, 2, '2024-01-18 05:25:00', '2024-01-18 05:25:00', NULL);

INSERT INTO "FormQuestions" ("question", "is_required", "type", "question_order", "form_template_id") VALUES
('Turno', TRUE, 'text', 1, 1),
('Numero del surtidor', TRUE, 'text', 2, 1),
('Estado del surtidor', TRUE, 'boolean', 3, 1),
('Estado de manguera de venteo', TRUE, 'boolean', 4, 1),
('Número de Upkeep general', FALSE, 'text', 5, 1),
('Comentarios generales', FALSE, 'text', 6, 1),
('Tomar foto', TRUE, 'boolean', 7, 1),
('Estado de manguera de suministro', TRUE, 'boolean', 8, 1),
('Número de Upkeep manguera suministro', FALSE, 'text', 9, 1),
('Estado de válvula NGVJ/fuga', TRUE, 'boolean', 10, 1),
('Número de Upkeep válvula', FALSE, 'text', 11, 1),
('Estado de válvula NGVJ 3 vías', TRUE, 'boolean', 12, 1),
('Número de Upkeep 3 vías', FALSE, 'text', 13, 1),
('Estado de válvula NGVJ acople', TRUE, 'boolean', 14, 1),
('Número de Upkeep NGVJ acople', FALSE, 'text', 15, 1),
('Estatus', TRUE, 'boolean', 1, 2),
('Nivel jabón de manos', FALSE, 'text', 2, 2),
('Cantidad de papel', FALSE, 'text', 3, 2),
('Nivel de basura en el bote', FALSE, 'text', 4, 2),
('Tomar foto', TRUE, 'boolean', 5, 2);

INSERT INTO "FormAnswers" ("question_id", "work_order_id", "answer", "area", "comments", "image") VALUES
(1, 1, 'Turno 1', NULL, 'Turno matutino', NULL),
(2, 1, '3', NULL, 'Surtidor número 3', NULL),
(3, 1, 'true', 'Cara 1', 'OK - Funcionando', 'surtidor_3_cara1_estado.jpg'),
(4, 1, 'true', 'Cara 1', 'En buen estado', 'surtidor_3_cara1_manguera_venteo.jpg'),
(7, 1, 'true', 'Cara 1', 'Foto tomada', 'surtidor_3_cara1_foto.jpg'),
(8, 1, 'true', 'Cara 1', 'En buen estado', 'surtidor_3_cara1_manguera_suministro.jpg'),
(10, 1, 'true', 'Cara 1', 'Sin fugas', 'surtidor_3_cara1_valvula_fuga.jpg'),
(12, 1, 'true', 'Cara 1', 'Funcionando correctamente', 'surtidor_3_cara1_valvula_3vias.jpg'),
(14, 1, 'true', 'Cara 1', 'En buen estado', 'surtidor_3_cara1_valvula_ngvj.jpg'),
(16, 5, 'true', 'Luminarias', 'OK - Funcionando correctamente', 'bano_luminarias.jpg'),
(17, 5, '100%', 'Dispensador jabón', 'Completamente lleno', 'bano_dispensador_jabon.jpg'),
(18, 5, '100%', 'Dispensador papel', 'Completamente lleno', 'bano_dispensador_papel.jpg'),
(19, 5, '10%', 'Bote de basura', 'Casi vacío', 'bano_basura.jpg'),
(20, 5, 'true', 'General', 'Foto tomada del baño', 'bano_general.jpg');

CREATE INDEX IF NOT EXISTS idx_users_email ON "Users"("email");
CREATE INDEX IF NOT EXISTS idx_work_order_status ON "WorkOrder"("status");
CREATE INDEX IF NOT EXISTS idx_work_order_date ON "WorkOrder"("date");
CREATE INDEX IF NOT EXISTS idx_work_order_eds ON "WorkOrder"("eds_id");
CREATE INDEX IF NOT EXISTS idx_eds_plaza ON "EDS"("plaza");
CREATE INDEX IF NOT EXISTS idx_form_answers_question ON "FormAnswers"("question_id");
CREATE INDEX IF NOT EXISTS idx_form_answers_work_order ON "FormAnswers"("work_order_id");
