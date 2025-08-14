-- Limpiar todas las tablas en orden (respetando foreign keys)
DELETE FROM "FormAnswers";
DELETE FROM "WorkOrder";
DELETE FROM "Users";
DELETE FROM "EDS";
DELETE FROM "FormQuestions";
DELETE FROM "Roles";
DELETE FROM "Permissions";

-- Reiniciar secuencias (opcional)
ALTER SEQUENCE "Users_id_usr_pk_seq" RESTART WITH 1;
ALTER SEQUENCE "Roles_id_rol_pk_seq" RESTART WITH 1;
ALTER SEQUENCE "Permissions_id_permissions_pk_seq" RESTART WITH 1;
ALTER SEQUENCE "WorkOrder_id_work_order_pk_seq" RESTART WITH 1;
ALTER SEQUENCE "EDS_id_eds_pk_seq" RESTART WITH 1;
ALTER SEQUENCE "FormQuestions_id_question_form_pk_seq" RESTART WITH 1;
ALTER SEQUENCE "FormAnswers_id_answer_form_pk_seq" RESTART WITH 1;
