#!/usr/bin/env python3
"""Writes the consumer-support track (questions/consumer_en.json, consumer_ar.json).

Each item: question + expected answer taken ONLY from the cited public help page, read 2026-11-17.
Arabic text: where the source page has an Arabic version (ar_source set) the answer follows it;
otherwise (Jumbo, Apple: no Arabic text on the page) the Arabic was drafted by the benchmark author
from the English page. NO Arabic reader has checked any of it yet."""
import json, pathlib
OUT = pathlib.Path(__file__).resolve().parent.parent / "questions"
D = "2026-11-17"
SAM = "https://www.samsung.com/ae/support/apps-services/what-is-the-return-policy-for-online-purchases-in-uae-bahrain-kuwait-oman-and-qatar/"
SAM_AR = "https://www.samsung.com/ae_ar/support/apps-services/what-is-the-return-policy-for-online-purchases-in-uae-bahrain-kuwait-oman-and-qatar/"
JUM = "https://www.jumbo.ae/customer-support/return-and-exchange"
APP = "https://www.apple.com/ae-business/shop/help/returns_refund"
CP = "https://helpae.centrepointstores.com/en/support/solutions/articles/44001702321-how-do-i-return-an-order-"
CP_AR = "https://helpae.centrepointstores.com/ar/support/solutions/articles/44001702321"
# (n, category, src_en, src_ar, ar_native, q_en, a_en, q_ar, a_ar)
ITEMS = [
("returns",SAM,SAM_AR,True,"Within how many days can an unopened item bought online from this retailer's UAE store be returned?","Unopened items can be returned within 14 days.","خلال كم يومًا يمكن إرجاع منتج غير مفتوح تم شراؤه عبر الإنترنت من متجر هذا البائع في الإمارات؟","يُسمح بإرجاع المنتجات غير المفتوحة خلال 14 يومًا."),
("returns",SAM,SAM_AR,True,"Does the return policy treat TVs and home appliances differently after delivery?","Yes. TVs and home appliances have specific restrictions after delivery.","هل تعامل سياسة الإرجاع أجهزة التلفزيون والأجهزة المنزلية بشكل مختلف بعد التسليم؟","نعم، تخضع أجهزة التلفزيون والأجهزة المنزلية لشروط وقيود خاصة بعد التسليم."),
("returns",SAM,SAM_AR,True,"Does cancelling an online order follow the same rule as returning an item?","No. Returns are allowed for unopened items within 14 days, while cancellation depends on the status of the order.","هل يتبع إلغاء الطلب عبر الإنترنت القاعدة نفسها المتبعة في إرجاع المنتج؟","لا. يُسمح بإرجاع المنتجات غير المفتوحة خلال 14 يومًا، بينما يعتمد إلغاء الطلب على حالة الطلب."),
("returns",JUM,None,False,"How long after delivery or in-store collection can a customer ask this electronics retailer for a return or exchange?","Within seven (7) days from the date of delivery or in-store collection.","بعد كم يومًا من التسليم أو الاستلام من المتجر يمكن للعميل طلب إرجاع أو استبدال من متجر الإلكترونيات هذا؟","خلال سبعة (7) أيام من تاريخ التسليم أو الاستلام من المتجر."),
("returns",JUM,None,False,"What restocking fee applies to non-defective opened items returned within the allowed period?","A restocking fee of fifteen percent (15%).","ما رسوم إعادة التخزين المطبقة على المنتجات المفتوحة غير المعيبة التي تُرجع خلال المدة المسموحة؟","رسوم إعادة تخزين بنسبة خمسة عشر بالمئة (15%)."),
("refunds",JUM,None,False,"How are online refunds paid, and within how many business days after the return is approved?","Refunds go to the original method of payment only (purchases made with gift cards or Etihad Miles are refunded as gift vouchers), and are processed within seven (7) business days of return approval.","كيف تُدفع المبالغ المستردة للطلبات عبر الإنترنت، وخلال كم يوم عمل بعد الموافقة على الإرجاع؟","تُرد المبالغ إلى وسيلة الدفع الأصلية فقط (والمشتريات التي دُفعت ببطاقات الهدايا أو أميال الاتحاد تُرد على شكل قسائم هدايا)، وتُعالج خلال سبعة (7) أيام عمل من الموافقة على الإرجاع."),
("refunds",JUM,None,False,"Which charges are non-refundable once acknowledged?","Delivery, service, installation and restocking fees (if applicable).","ما الرسوم غير القابلة للاسترداد بعد الإقرار بها؟","رسوم التوصيل والخدمة والتركيب وإعادة التخزين (إن وجدت)."),
("returns",JUM,None,False,"Can headphones or earphones be returned?","No. Headphones/earphones are listed among the non-returnable categories.","هل يمكن إرجاع سماعات الرأس أو سماعات الأذن؟","لا. سماعات الرأس والأذن مدرجة ضمن الفئات غير القابلة للإرجاع."),
("returns",JUM,None,False,"Can open-box and display units be returned?","They are final sale, except where the item is proven defective within seven (7) days of delivery or collection.","هل يمكن إرجاع المنتجات المفتوحة وأجهزة العرض؟","هي بيع نهائي، إلا إذا ثبت أن المنتج معيب خلال سبعة (7) أيام من التسليم أو الاستلام."),
("refunds",JUM,None,False,"What happens to a coupon discount when an item bought with a coupon code is returned?","Discounts redeemed from coupon codes are non-refundable and are deducted from the total refund amount.","ماذا يحدث لخصم القسيمة عند إرجاع منتج تم شراؤه برمز قسيمة؟","الخصومات المستردة من رموز القسائم غير قابلة للاسترداد وتُخصم من إجمالي مبلغ الاسترداد."),
("returns",APP,None,False,"Within how many calendar days of delivery can standard hardware be returned if the customer changes their mind?","Within 14 calendar days of delivery.","خلال كم يومًا تقويميًا من التسليم يمكن إرجاع الأجهزة القياسية إذا غيّر العميل رأيه؟","خلال 14 يومًا تقويميًا من التسليم."),
("returns",APP,None,False,"Can software be returned, and under what condition?","Yes, within the same 14-day period, but only if the software was not unsealed.","هل يمكن إرجاع البرمجيات، وبأي شرط؟","نعم، خلال فترة الـ14 يومًا نفسها، ولكن فقط إذا لم يتم فتح ختم البرنامج."),
("refunds",APP,None,False,"When are refunds sent to the card-issuing bank for a credit or debit card payment?","Within five business days of receipt of the returned item or the cancellation request.","متى تُرسل المبالغ المستردة إلى البنك المصدر للبطاقة عند الدفع ببطاقة ائتمان أو خصم؟","خلال خمسة أيام عمل من استلام المنتج المرتجع أو طلب الإلغاء."),
("refunds",APP,None,False,"How is a purchase paid with a gift card refunded?","It is refunded as a gift card, sent by email.","كيف يُسترد ثمن مشتريات دُفعت باستخدام بطاقة هدايا؟","يُرد على شكل بطاقة هدايا ترسل عبر البريد الإلكتروني."),
("refunds",APP,None,False,"After the goods are back at the warehouse, how long should a customer allow for the refund to reach their account?","Please allow 5-7 days for the refund to reach the account.","بعد وصول البضائع إلى المستودع، كم من الوقت ينبغي للعميل انتظاره لوصول المبلغ المسترد إلى حسابه؟","يُرجى الانتظار من 5 إلى 7 أيام لوصول المبلغ المسترد إلى الحساب."),
("returns",CP,CP_AR,True,"In how many ways can an order be returned, and what are they?","Three: request a return online, return to a store, or call for a pick-up.","بكم طريقة يمكن إرجاع الطلب، وما هي؟","بثلاث طرق: طلب إرجاع أونلاين، أو الإرجاع إلى المتجر، أو الاتصال لاستلام المرتجع."),
("refunds",CP,CP_AR,True,"For an online return, how long does the refund to a card, bank account, PayPal or Tabby account take after the returns are checked?","Within 4-15 days.","عند الإرجاع أونلاين، كم تستغرق إعادة المبلغ إلى البطاقة أو الحساب المصرفي أو باي بال أو تابي بعد التحقق من المرتجعات؟","خلال 4 إلى 15 يومًا."),
("refunds",CP,CP_AR,True,"What does a registered customer who paid cash for an online return receive, and what does a guest customer who paid cash receive?","A registered customer receives the refund to My Credit in their account; a guest customer who paid cash receives a Return Voucher.","ماذا يتلقى العميل المسجل الذي دفع نقدًا عند الإرجاع أونلاين، وماذا يتلقى العميل الزائر الذي دفع نقدًا؟","يتلقى العميل المسجل المبلغ في «رصيدي» في حسابه، أما العميل الزائر الذي دفع نقدًا فيتسلم قسيمة إرجاع."),
("returns",CP,CP_AR,True,"Where can Iconic products be returned?","Iconic products can only be returned to an Iconic store.","أين يمكن إرجاع منتجات آيكونيك؟","يمكن إرجاع منتجات آيكونيك فقط إلى متجر آيكونيك."),
("refunds",CP,CP_AR,True,"What refund options does a customer who paid cash have when returning to a store?","They can ask for a cash refund, a Credit Note usable in-store or online, or a refund to My Credit in their account.","ما خيارات الاسترداد المتاحة للعميل الذي دفع نقدًا عند الإرجاع إلى المتجر؟","يمكنه طلب استرداد نقدي، أو مذكرة ائتمان يمكن استخدامها في المتجر أو أونلاين، أو ردّ المبلغ إلى «رصيدي» في حسابه."),
]
en, ar = [], []
for i, (cat, s_en, s_ar, nat, qe, ae, qa, aa) in enumerate(ITEMS, 1):
    en.append(dict(id=f"CON-EN-{i:03d}", track="consumer", category=cat, question=qe, expected_answer=ae, source_url=s_en, date_read=D))
    ar.append(dict(id=f"CON-AR-{i:03d}", track="consumer", category=cat, question=qa, expected_answer=aa, source_url=s_ar or s_en, date_read=D,
                   arabic_basis="arabic_source_page" if nat else "drafted_from_english_page", arabic_checked_by_reader=False))
(OUT/"consumer_en.json").write_text(json.dumps(en, ensure_ascii=False, indent=1))
(OUT/"consumer_ar.json").write_text(json.dumps(ar, ensure_ascii=False, indent=1))
print(len(en), len(ar))
