// Iran deployment config (edit prices before production!)
export const SITE = {
  id:'ir', lang:'fa', dir:'rtl',
  name:'نرس پلاس', currency:'IRT', gateway:'zarinpal',
  plans:[
    { code:'m1',  months:1,  price:'۸۹۰٬۰۰۰ تومان'  },
    { code:'m6',  months:6,  price:'۴٬۵۰۰٬۰۰۰ تومان' },
    { code:'m12', months:12, price:'۸٬۰۰۰٬۰۰۰ تومان' },
  ],
  checkoutNote:'پرداخت واقعی نیازمند backend است — فعلاً استاب.',
};