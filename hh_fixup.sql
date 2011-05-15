
insert into offices
select 0+id, name, fax, address, notes
from Office;

insert into officers
select 0+id, name, email, office
from Officer;

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
from Visit;

create table current_clients as
select * from (
select max(s.date) last_seen, c.id
from clients c
join visits v on v.client = c.id
join sessions s on v.session = s.id
where s.date != '--' -- done with this now?
 and s.group_id > 0
group by c.id
) t
where julianday('now') - julianday(last_seen) < 60
order by t.last_seen desc
;

create table current_visits as
select v.*
from visits v
join current_clients cc
  on v.client = cc.id
;

create table current_sessions as
select distinct s.*
from current_visits v
join sessions s
  on v.session = s.id
order by s.date desc
;

create table id_map (
 t text,
 did integer,
 zid integer,
 primary key (t, zid)
)
;