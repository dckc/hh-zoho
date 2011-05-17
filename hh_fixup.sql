
insert into offices
select 0+id, name, fax, address, notes
from Office
where name > '';

insert into officers
select 0+id, name, email, office
from Officer
where name > '';

insert into batches
select 0+id, name
from Batch;

insert into clients
select 0+id, name, ins, approval, dx, note
     , case when officer > ''
       then 0+officer else null end
     , dob, address, phone
     , case when batch > ''
       then 0+batch else null end
from Client;

insert into groups
select 0+id, Name
     , 0+substr(rate, length('USD $.'))
     , case Eval when 'Yes' then 1 else 0 end
from "Group";

insert into sessions
select 0+id 
     , substr(date, 7, 4) || '-' ||
       substr(date, 1, 2) || '-' ||
       substr(date, 4, 2)
     , 0+"group", time, therapist
from Session
where date > '' and "group" > '';

insert into visits
select 0+id, 0+session, 0+client, attend
     , 0+substr(client_pd, length('USD $.'))
     , note
     , case when bill_date > '' then
       substr(bill_date, 7, 4) || '-' ||
       substr(bill_date, 1, 2) || '-' ||
       substr(bill_date, 4, 2)
       else null end
     , case when check_date > '' then
       substr(check_date, 7, 4) || '-' ||
       substr(check_date, 1, 2) || '-' ||
       substr(check_date, 4, 2)
       else null end
     , case when "INS_PAID_$" > ''
       then 0+substr("INS_PAID_$", length('USD $.'))
       else null end
from Visit
where session > '' and client > '';

create table current_clients as
select c.* from clients c
join (
  select max(s.date) last_seen, c.id
  from clients c
  join visits v on v.client = c.id
  join sessions s on v.session = s.id
  group by c.id
  ) t
on t.id == c.id
where julianday('now') - julianday(t.last_seen) < 10 -- @@ 60
;

create table current_visits as
select v.*
from visits v
join current_clients cc
  on v.client = cc.id
;

create table current_sessions as
select s.*
from sessions s
join (select distinct session from current_visits) v
  on v.session = s.id
;

create table id_map (
 t text,
 did integer,
 zid text,
 primary key (t, zid)
)
;