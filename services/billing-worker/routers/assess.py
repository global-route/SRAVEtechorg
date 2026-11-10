from fastapi import APIRouter, HTTPException
from providers.whatsapp import send_demand_notice
from providers.flutterwave import create_payment_link

router = APIRouter()


@router.post("/assess/{building_id}", status_code=201)
async def assess(building_id: int):
    # TODO: query building + tax_roll + tax_rates from DB
    try:
        payment_link = await create_payment_link(
            assessment_id=f"asmnt_{building_id}",
            amount_ngn=50000.0,
        )
        await send_demand_notice(
            phone="+2348000000000",
            owner_name="Property Owner",
            address="123 Test Street",
            amount="50,000",
            payment_link=payment_link,
            ref=f"asmnt_{building_id}",
        )
        return {
            "assessment_id": f"asmnt_{building_id}",
            "building_id": building_id,
            "wa_status": "delivered",
            "payment_link": payment_link,
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
