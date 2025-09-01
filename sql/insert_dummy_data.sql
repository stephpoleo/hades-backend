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

INSERT INTO "WorkOrder" ("date", "status", "id_usr_fk", "id_eds_fk", "id_form_template_fk", "start_date_time", "end_date_time") VALUES
('2024-01-15', 'completed', 1, 1, 1, '2024-01-15 07:41:00', '2024-01-15 07:43:00'),
('2024-01-20', 'completed', 2, 2, 1, '2024-01-20 08:15:00', '2024-01-20 08:45:00'),
('2024-01-10', 'completed', 3, 3, 1, '2024-01-10 09:30:00', '2024-01-10 10:15:00'),
('2024-01-25', 'pending', 4, 1, 1, '2024-01-25 14:00:00', NULL),
('2024-01-18', 'completed', 2, 1, 2, '2024-01-18 05:25:00', '2024-01-18 05:25:00');

INSERT INTO "FormQuestions" ("question", "is_required", "type", "id_form_template_fk", "question_order") VALUES
('Turno', TRUE, 'text', 1, 1),
('Numero del surtidor', TRUE, 'text', 1, 2),
('Estado del surtidor', TRUE, 'boolean', 1, 3),
('Estado de manguera de venteo', TRUE, 'boolean', 1, 4),
('Número de Upkeep general', FALSE, 'text', 1, 5),
('Comentarios generales', FALSE, 'text', 1, 6),
('Tomar foto', TRUE, 'boolean', 1, 7),
('Estado de manguera de suministro', TRUE, 'boolean', 1, 8),
('Número de Upkeep manguera suministro', FALSE, 'text', 1, 9),
('Estado de válvula NGVJ/fuga', TRUE, 'boolean', 1, 10),
('Número de Upkeep válvula', FALSE, 'text', 1, 11),
('Estado de válvula NGVJ 3 vías', TRUE, 'boolean', 1, 12),
('Número de Upkeep 3 vías', FALSE, 'text', 1, 13),
('Estado de válvula NGVJ acople', TRUE, 'boolean', 1, 14),
('Número de Upkeep NGVJ acople', FALSE, 'text', 1, 15),
('Estatus', TRUE, 'boolean', 2, 1),
('Nivel jabón de manos', FALSE, 'text', 2, 2),
('Cantidad de papel', FALSE, 'text', 2, 3),
('Nivel de basura en el bote', FALSE, 'text', 2, 4),
('Tomar foto', TRUE, 'boolean', 2, 5);

INSERT INTO "FormAnswers" ("id_question_form_fk", "work_order_id", "answer", "area", "comments", "image") VALUES
(1, 1, 'Turno 1', NULL, 'Turno matutino', NULL),
(2, 1, '3', NULL, 'Surtidor número 3', NULL),
(3, 1, 'true', 'Cara 1', 'OK - Funcionando', 'surtidor_3_cara1_estado.jpg'),
(4, 1, 'true', 'Cara 1', 'En buen estado', 'surtidor_3_cara1_manguera_venteo.jpg'),
(5, 1, NULL, 'Cara 1', 'N/A', NULL),
(6, 1, NULL, 'Cara 1', 'N/A', NULL),
(7, 1, 'true', 'Cara 1', 'Foto tomada', 'surtidor_3_cara1_foto.jpg'),
(8, 1, 'true', 'Cara 1', 'En buen estado', 'surtidor_3_cara1_manguera_suministro.jpg'),
(9, 1, NULL, 'Cara 1', 'N/A', NULL),
(10, 1, 'true', 'Cara 1', 'Sin fugas', 'surtidor_3_cara1_valvula_fuga.jpg'),
(11, 1, NULL, 'Cara 1', 'N/A', NULL),
(12, 1, 'true', 'Cara 1', 'Funcionando correctamente', 'surtidor_3_cara1_valvula_3vias.jpg'),
(13, 1, NULL, 'Cara 1', 'N/A', NULL),
(14, 1, 'true', 'Cara 1', 'En buen estado', 'surtidor_3_cara1_valvula_ngvj.jpg'),
(15, 1, NULL, 'Cara 1', 'N/A', NULL),
(3, 1, 'true', 'Cara 2', 'OK - Funcionando', 'surtidor_3_cara2_estado.jpg'),
(4, 1, 'true', 'Cara 2', 'En buen estado', 'surtidor_3_cara2_manguera_venteo.jpg'),
(5, 1, NULL, 'Cara 2', 'N/A', NULL),
(6, 1, NULL, 'Cara 2', 'N/A', NULL),
(7, 1, 'true', 'Cara 2', 'Foto tomada', 'surtidor_3_cara2_foto.jpg'),
(8, 1, 'true', 'Cara 2', 'En buen estado', 'surtidor_3_cara2_manguera_suministro.jpg'),
(9, 1, NULL, 'Cara 2', 'N/A', NULL),
(10, 1, 'true', 'Cara 2', 'Sin fugas', 'surtidor_3_cara2_valvula_fuga.jpg'),
(11, 1, NULL, 'Cara 2', 'N/A', NULL),
(12, 1, 'true', 'Cara 2', 'Funcionando correctamente', 'surtidor_3_cara2_valvula_3vias.jpg'),
(13, 1, NULL, 'Cara 2', 'N/A', NULL),
(14, 1, 'true', 'Cara 2', 'En buen estado', 'surtidor_3_cara2_valvula_ngvj.jpg'),
(15, 1, NULL, 'Cara 2', 'N/A', NULL),

(2, 1, '10', NULL, 'Surtidor número 10', NULL),
(3, 1, 'true', 'Cara 1', 'OK - Funcionando', 'surtidor_10_cara1_estado.jpg'),
(4, 1, 'true', 'Cara 1', 'En buen estado', 'surtidor_10_cara1_manguera_venteo.jpg'),
(5, 1, NULL, 'Cara 1', 'N/A', NULL),
(6, 1, NULL, 'Cara 1', 'N/A', NULL),
(7, 1, 'true', 'Cara 1', 'Foto tomada', 'surtidor_10_cara1_foto.jpg'),
(8, 1, 'true', 'Cara 1', 'En buen estado', 'surtidor_10_cara1_manguera_suministro.jpg'),
(9, 1, NULL, 'Cara 1', 'N/A', NULL),
(10, 1, 'true', 'Cara 1', 'Sin fugas', 'surtidor_10_cara1_valvula_fuga.jpg'),
(11, 1, NULL, 'Cara 1', 'N/A', NULL),
(12, 1, 'true', 'Cara 1', 'Funcionando correctamente', 'surtidor_10_cara1_valvula_3vias.jpg'),
(13, 1, NULL, 'Cara 1', 'N/A', NULL),
(14, 1, 'true', 'Cara 1', 'En buen estado', 'surtidor_10_cara1_valvula_ngvj.jpg'),
(15, 1, NULL, 'Cara 1', 'N/A', NULL),

(3, 1, 'true', 'Cara 2', 'OK - Funcionando', 'surtidor_10_cara2_estado.jpg'),
(4, 1, 'true', 'Cara 2', 'En buen estado', 'surtidor_10_cara2_manguera_venteo.jpg'),
(5, 1, NULL, 'Cara 2', 'N/A', NULL),
(6, 1, NULL, 'Cara 2', 'N/A', NULL),
(7, 1, 'true', 'Cara 2', 'Foto tomada', 'surtidor_10_cara2_foto.jpg'),
(8, 1, 'true', 'Cara 2', 'En buen estado', 'surtidor_10_cara2_manguera_suministro.jpg'),
(9, 1, NULL, 'Cara 2', 'N/A', NULL),
(10, 1, 'true', 'Cara 2', 'Sin fugas', 'surtidor_10_cara2_valvula_fuga.jpg'),
(11, 1, NULL, 'Cara 2', 'N/A', NULL),
(12, 1, 'true', 'Cara 2', 'Funcionando correctamente', 'surtidor_10_cara2_valvula_3vias.jpg'),
(13, 1, NULL, 'Cara 2', 'N/A', NULL),
(14, 1, 'true', 'Cara 2', 'En buen estado', 'surtidor_10_cara2_valvula_ngvj.jpg'),
(15, 1, NULL, 'Cara 2', 'N/A', NULL),

(16, 5, 'true', 'Luminarias', 'OK - Funcionando correctamente', 'bano_luminarias.jpg'),
(17, 5, '0%', 'Luminarias', 'No aplica para luminarias', NULL),
(18, 5, '0%', 'Luminarias', 'No aplica para luminarias', NULL),
(19, 5, '0%', 'Luminarias', 'No aplica para luminarias', NULL),
(20, 5, 'true', 'Luminarias', 'Foto tomada', 'bano_luminarias.jpg'),

(16, 5, 'true', 'Sensor de movimiento', 'OK - Funcionando correctamente', 'bano_sensor_movimiento.jpg'),
(17, 5, '0%', 'Sensor de movimiento', 'No aplica', NULL),
(18, 5, '0%', 'Sensor de movimiento', 'No aplica', NULL),
(19, 5, '0%', 'Sensor de movimiento', 'No aplica', NULL),
(20, 5, 'true', 'Sensor de movimiento', 'Foto tomada', 'bano_sensor_movimiento.jpg'),

(16, 5, 'true', 'Estado de dispensador de jabón', 'OK - Funcionando', 'bano_dispensador_jabon.jpg'),
(17, 5, '100%', 'Estado de dispensador de jabón', 'Completamente lleno', NULL),
(18, 5, '0%', 'Estado de dispensador de jabón', 'No aplica', NULL),
(19, 5, '0%', 'Estado de dispensador de jabón', 'No aplica', NULL),
(20, 5, 'true', 'Estado de dispensador de jabón', 'Foto tomada', 'bano_dispensador_jabon.jpg'),

(16, 5, 'true', 'Estado de dispensador de papel', 'OK - Funcionando', 'bano_dispensador_papel.jpg'),
(17, 5, '0%', 'Estado de dispensador de papel', 'No aplica', NULL),
(18, 5, '100%', 'Estado de dispensador de papel', 'Completamente lleno', NULL),
(19, 5, '0%', 'Estado de dispensador de papel', 'No aplica', NULL),
(20, 5, 'true', 'Estado de dispensador de papel', 'Foto tomada', 'bano_dispensador_papel.jpg'),

(16, 5, 'true', 'Mingitorios', 'OK - Limpios y funcionando', 'bano_mingitorios.jpg'),
(17, 5, '0%', 'Mingitorios', 'No aplica', NULL),
(18, 5, '0%', 'Mingitorios', 'No aplica', NULL),
(19, 5, '0%', 'Mingitorios', 'No aplica', NULL),
(20, 5, 'true', 'Mingitorios', 'Foto tomada', 'bano_mingitorios.jpg'),

(16, 5, 'true', 'Tazas', 'OK - Limpias y funcionando', 'bano_tazas.jpg'),
(17, 5, '0%', 'Tazas', 'No aplica', NULL),
(18, 5, '0%', 'Tazas', 'No aplica', NULL),
(19, 5, '0%', 'Tazas', 'No aplica', NULL),
(20, 5, 'true', 'Tazas', 'Foto tomada', 'bano_tazas.jpg'),

(16, 5, 'true', 'Lavabo', 'OK - Limpio y funcionando', 'bano_lavabo.jpg'),
(17, 5, '0%', 'Lavabo', 'No aplica', NULL),
(18, 5, '0%', 'Lavabo', 'No aplica', NULL),
(19, 5, '0%', 'Lavabo', 'No aplica', NULL),
(20, 5, 'true', 'Lavabo', 'Foto tomada', 'bano_lavabo.jpg'),

(16, 5, 'true', 'Paredes y puertas', 'OK - En buen estado', 'bano_paredes_puertas.jpg'),
(17, 5, '0%', 'Paredes y puertas', 'No aplica', NULL),
(18, 5, '0%', 'Paredes y puertas', 'No aplica', NULL),
(19, 5, '0%', 'Paredes y puertas', 'No aplica', NULL),
(20, 5, 'true', 'Paredes y puertas', 'Foto tomada', 'bano_paredes_puertas.jpg'),

(16, 5, 'true', 'Extractor', 'OK - Funcionando correctamente', 'bano_extractor.jpg'),
(17, 5, '0%', 'Extractor', 'No aplica', NULL),
(18, 5, '0%', 'Extractor', 'No aplica', NULL),
(19, 5, '0%', 'Extractor', 'No aplica', NULL),
(20, 5, 'true', 'Extractor', 'Foto tomada', 'bano_extractor.jpg'),

(16, 5, 'true', 'Puerta principal', 'OK - Funcionando correctamente', 'bano_puerta_principal.jpg'),
(17, 5, '0%', 'Puerta principal', 'No aplica', NULL),
(18, 5, '0%', 'Puerta principal', 'No aplica', NULL),
(19, 5, '0%', 'Puerta principal', 'No aplica', NULL),
(20, 5, 'true', 'Puerta principal', 'Foto tomada', 'bano_puerta_principal.jpg'),

(16, 5, 'true', 'Secador de manos', 'OK - Funcionando correctamente', 'bano_secador_manos.jpg'),
(17, 5, '0%', 'Secador de manos', 'No aplica', NULL),
(18, 5, '0%', 'Secador de manos', 'No aplica', NULL),
(19, 5, '0%', 'Secador de manos', 'No aplica', NULL),
(20, 5, 'true', 'Secador de manos', 'Foto tomada', 'bano_secador_manos.jpg');

CREATE INDEX IF NOT EXISTS idx_users_email ON "Users"("email");
CREATE INDEX IF NOT EXISTS idx_work_order_status ON "WorkOrder"("status");
CREATE INDEX IF NOT EXISTS idx_work_order_date ON "WorkOrder"("date");
CREATE INDEX IF NOT EXISTS idx_work_order_user ON "WorkOrder"("id_usr_fk");
CREATE INDEX IF NOT EXISTS idx_work_order_eds ON "WorkOrder"("id_eds_fk");
CREATE INDEX IF NOT EXISTS idx_work_order_template ON "WorkOrder"("id_form_template_fk");
CREATE INDEX IF NOT EXISTS idx_eds_plaza ON "EDS"("plaza");
CREATE INDEX IF NOT EXISTS idx_form_answers_question ON "FormAnswers"("id_question_form_fk");
CREATE INDEX IF NOT EXISTS idx_form_answers_work_order ON "FormAnswers"("work_order_id");
CREATE INDEX IF NOT EXISTS idx_form_questions_template ON "FormQuestions"("id_form_template_fk");