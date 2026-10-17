// International deployment config (edit prices before production!)
export const SITE = {
  id:'com', lang:'en', dir:'ltr',
  name:'Nurse Plus', currency:'USD', gateway:'stripe',
  plans:[
    { code:'m1',  months:1,  price:'$4.99'  },
    { code:'m6',  months:6,  price:'$19.99' },
    { code:'m12', months:12, price:'$39.99' },
  ],
  checkoutNote:'Real checkout needs a backend — stub for now.',
};